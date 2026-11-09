#include <Arduino.h>
#include "driver/pcnt.h"
#include "RL_ESP32_Motor.h"
#include "ESP32_Servo.h"
#include "config.h"

/*
 * ESP32 IOT&Robot Board (4Motor) - four-wheel RPM PID chassis
 *
 * Serial packet (115200 baud, little-endian, 7 x int16_t):
 * [M1 RPM, M2 RPM, M3 RPM, M4 RPM, servo1, servo2, -12345]
 *
 * A valid command remains active for at most SERIAL_WATCHDOG_MS.
 * Send four zero RPM values to stop normally.
 */

enum PacketField { M0 = 0, M1, M2, M3, S1, S2, CHECK };

constexpr size_t PACKET_FIELD_COUNT = 7;
constexpr size_t PACKET_SIZE = PACKET_FIELD_COUNT * sizeof(int16_t);
constexpr int16_t CHECK_VALUE = -12345;

// Set true only for bench testing one raised wheel at a time.
constexpr float SELF_TEST_TARGETS[] = {
    0, 100, 150, 200, 0, -100, -150, -200, 0
};
constexpr size_t SELF_TEST_TARGET_COUNT =
    sizeof(SELF_TEST_TARGETS) / sizeof(SELF_TEST_TARGETS[0]);

Motor motors[MOTOR_COUNT] = {
    Motor(1, MOTOR_A_PINS[0], MOTOR_B_PINS[0]),
    Motor(2, MOTOR_A_PINS[1], MOTOR_B_PINS[1]),
    Motor(3, MOTOR_A_PINS[2], MOTOR_B_PINS[2]),
    Motor(4, MOTOR_A_PINS[3], MOTOR_B_PINS[3])
};

Servo servo1;
Servo servo2;

const pcnt_unit_t PCNT_UNITS[MOTOR_COUNT] = {
    PCNT_UNIT_0, PCNT_UNIT_1, PCNT_UNIT_2, PCNT_UNIT_3
};

struct MotorPidState {
  float targetRpm = 0.0f;
  float measuredRpm = 0.0f;
  float rawRpm = 0.0f;
  float integral = 0.0f;
  float previousError = 0.0f;
  int16_t pwm = 0;
  int8_t previousDirection = 0;
  uint32_t startupKickEndMs = 0;
  uint32_t directionGraceEndMs = 0;
  uint8_t wrongDirectionCycles = 0;
  bool directionFault = false;
};

MotorPidState pid[MOTOR_COUNT];
int16_t packetStatus[PACKET_FIELD_COUNT] = {0, 0, 0, 0, 110, 90, 0};
uint32_t previousControlMs = 0;
uint32_t previousUltrasonicMs = 0;
bool obstacleStop = false;
size_t selfTestStage = 0;
uint32_t selfTestStageStartMs = 0;
uint32_t selfTestPrintMs = 0;
uint32_t lastValidCommandMs = 0;
bool watchdogReported = false;

int8_t signOf(float value) {
  if (value > 0.01f) return 1;
  if (value < -0.01f) return -1;
  return 0;
}

void applyMotorPwm(size_t index, int16_t signedPwm) {
  signedPwm = constrain(signedPwm, -MAX_PWM_OUTPUT, MAX_PWM_OUTPUT);
  pid[index].pwm = signedPwm;

  // Motor_Speed uses -100..100 percent; PID uses the tested 0..255 scale.
  const float dutyPercent = signedPwm * (100.0f / 255.0f);
  motors[index].Motor_Speed(dutyPercent);
}

void resetPid(size_t index) {
  pid[index].integral = 0.0f;
  pid[index].previousError = 0.0f;
}

void setMotorTarget(size_t index, float target, uint32_t now,
                    bool clearFault = false) {
  target = constrain(target, -MAX_TARGET_RPM, MAX_TARGET_RPM);
  const int8_t direction = signOf(target);

  if (clearFault) {
    pid[index].directionFault = false;
    pid[index].wrongDirectionCycles = 0;
  }

  if (direction != pid[index].previousDirection) {
    resetPid(index);
    pid[index].wrongDirectionCycles = 0;
    pid[index].directionFault = false;
    if (direction != 0) {
      pid[index].startupKickEndMs = now + STARTUP_KICK_MS;
      pid[index].directionGraceEndMs = now + 700;
    }
  }

  pid[index].targetRpm = target;
  pid[index].previousDirection = direction;

  if (direction == 0) {
    pid[index].startupKickEndMs = 0;
    resetPid(index);
    applyMotorPwm(index, 0);
  }
}

void stopAllMotors(uint32_t now) {
  for (size_t i = 0; i < MOTOR_COUNT; ++i) {
    setMotorTarget(i, 0.0f, now);
  }
}

void configureEncoder(size_t index) {
  const uint8_t pinA = static_cast<uint8_t>(ENCODER_A_PINS[index]);
  const uint8_t pinB = static_cast<uint8_t>(ENCODER_B_PINS[index]);

  // GPIO34/35/36/39 do not have internal pull resistors.
  if (pinA >= 34) pinMode(pinA, INPUT);
  else pinMode(pinA, INPUT_PULLUP);
  if (pinB >= 34) pinMode(pinB, INPUT);
  else pinMode(pinB, INPUT_PULLUP);

  pcnt_config_t channelA = {};
  channelA.pulse_gpio_num = ENCODER_A_PINS[index];
  channelA.ctrl_gpio_num = ENCODER_B_PINS[index];
  channelA.lctrl_mode = PCNT_MODE_KEEP;
  channelA.hctrl_mode = PCNT_MODE_REVERSE;
  channelA.pos_mode = PCNT_COUNT_DEC;
  channelA.neg_mode = PCNT_COUNT_INC;
  channelA.counter_h_lim = 32767;
  channelA.counter_l_lim = -32768;
  channelA.unit = PCNT_UNITS[index];
  channelA.channel = PCNT_CHANNEL_0;
  ESP_ERROR_CHECK(pcnt_unit_config(&channelA));

  pcnt_config_t channelB = {};
  channelB.pulse_gpio_num = ENCODER_B_PINS[index];
  channelB.ctrl_gpio_num = ENCODER_A_PINS[index];
  channelB.lctrl_mode = PCNT_MODE_REVERSE;
  channelB.hctrl_mode = PCNT_MODE_KEEP;
  channelB.pos_mode = PCNT_COUNT_DEC;
  channelB.neg_mode = PCNT_COUNT_INC;
  channelB.counter_h_lim = 32767;
  channelB.counter_l_lim = -32768;
  channelB.unit = PCNT_UNITS[index];
  channelB.channel = PCNT_CHANNEL_1;
  ESP_ERROR_CHECK(pcnt_unit_config(&channelB));

  ESP_ERROR_CHECK(pcnt_counter_pause(PCNT_UNITS[index]));
  ESP_ERROR_CHECK(pcnt_filter_disable(PCNT_UNITS[index]));
  ESP_ERROR_CHECK(pcnt_counter_clear(PCNT_UNITS[index]));
  ESP_ERROR_CHECK(pcnt_counter_resume(PCNT_UNITS[index]));
}

void updateOnePid(size_t index, int16_t deltaCount, float dt,
                  uint32_t now) {
  MotorPidState &state = pid[index];
  state.rawRpm = ENCODER_SIGN[index] * static_cast<float>(deltaCount) *
                 60.0f / (COUNTS_PER_WHEEL_REV[index] * dt);
  state.measuredRpm +=
      RPM_FILTER_ALPHA * (state.rawRpm - state.measuredRpm);

  if (fabsf(state.targetRpm) < 0.01f || obstacleStop ||
      state.directionFault) {
    applyMotorPwm(index, 0);
    resetPid(index);
    return;
  }

  const int8_t targetDirection = signOf(state.targetRpm);

  // Encoder direction protection, after allowing startup time.
  if (static_cast<int32_t>(now - state.directionGraceEndMs) >= 0 &&
      fabsf(state.measuredRpm) > 5.0f &&
      signOf(state.measuredRpm) != targetDirection) {
    if (++state.wrongDirectionCycles >= 5) {
      state.directionFault = true;
      applyMotorPwm(index, 0);
      return;
    }
  } else {
    state.wrongDirectionCycles = 0;
  }

  if (static_cast<int32_t>(state.startupKickEndMs - now) > 0) {
    applyMotorPwm(index, targetDirection * STARTUP_PWM);
    return;
  }

  const float error = state.targetRpm - state.measuredRpm;
  const float derivative = (error - state.previousError) / dt;
  state.integral += error * dt;
  const float integralLimit = 140.0f / KI;
  state.integral = constrain(state.integral, -integralLimit, integralLimit);

  float output = FEED_FORWARD_PWM_PER_RPM * state.targetRpm +
                 KP * error + KI * state.integral + KD * derivative;
  if (targetDirection > 0) {
    output = constrain(output, 0.0f, static_cast<float>(MAX_PWM_OUTPUT));
  } else {
    output = constrain(output, -static_cast<float>(MAX_PWM_OUTPUT), 0.0f);
  }

  applyMotorPwm(index, static_cast<int16_t>(lroundf(output)));
  state.previousError = error;
}

void updateAllPid(uint32_t now) {
  if (now - previousControlMs < CONTROL_INTERVAL_MS) return;
  const uint32_t elapsedMs = now - previousControlMs;
  previousControlMs = now;
  const float dt = elapsedMs / 1000.0f;

  for (size_t i = 0; i < MOTOR_COUNT; ++i) {
    int16_t deltaCount = 0;
    ESP_ERROR_CHECK(pcnt_get_counter_value(PCNT_UNITS[i], &deltaCount));
    ESP_ERROR_CHECK(pcnt_counter_clear(PCNT_UNITS[i]));
    updateOnePid(i, deltaCount, dt, now);
  }
}

void updateUltrasonic(uint32_t now) {
  if (!ENABLE_ULTRASONIC_STOP ||
      now - previousUltrasonicMs < ULTRASONIC_INTERVAL_MS) return;
  previousUltrasonicMs = now;

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  const uint32_t duration = pulseIn(ECHO_PIN, HIGH, 25000);
  if (duration == 0) {
    obstacleStop = false;
    return;
  }
  const float distanceCm = duration * 0.034f / 2.0f;
  obstacleStop = distanceCm > 1.0f && distanceCm < STOP_DISTANCE_CM;
}

void setServoAngles(int16_t angle1, int16_t angle2) {
  if (!ENABLE_SERVOS) return;
  angle1 = constrain(angle1, 0, 180);
  angle2 = constrain(angle2, 0, 180);
  servo1.write(angle1);
  servo2.write(angle2);
  packetStatus[S1] = angle1;
  packetStatus[S2] = angle2;
}

void processControlPacket(uint32_t now) {
  if (Serial.available() < static_cast<int>(PACKET_SIZE)) return;

  int16_t packet[PACKET_FIELD_COUNT];
  const size_t bytesRead =
      Serial.readBytes(reinterpret_cast<char *>(packet), PACKET_SIZE);
  if (bytesRead != PACKET_SIZE || packet[CHECK] != CHECK_VALUE) {
    Serial.println("BAD");
    return;
  }

  lastValidCommandMs = now;
  watchdogReported = false;

  for (size_t i = 0; i < MOTOR_COUNT; ++i) {
    packetStatus[i] = packet[i];
    setMotorTarget(i, static_cast<float>(packet[i]), now);
  }
  setServoAngles(packet[S1], packet[S2]);

  bool anyFault = false;
  for (size_t i = 0; i < MOTOR_COUNT; ++i) {
    anyFault = anyFault || pid[i].directionFault;
  }
  if (obstacleStop) Serial.println("FAIL");
  else if (anyFault) Serial.println("FAULT");
  else Serial.println("SUCC");
}

void updateSelfTest(uint32_t now) {
  if (now - selfTestStageStartMs >= SELF_TEST_STAGE_MS) {
    selfTestStage = (selfTestStage + 1) % SELF_TEST_TARGET_COUNT;
    selfTestStageStartMs = now;
    stopAllMotors(now);
    setMotorTarget(SELF_TEST_MOTOR_INDEX,
                   SELF_TEST_TARGETS[selfTestStage], now, true);
    Serial.printf("SELF M%u target=%+.1f RPM\n",
                  static_cast<unsigned>(SELF_TEST_MOTOR_INDEX + 1),
                  SELF_TEST_TARGETS[selfTestStage]);
  }

  if (now - selfTestPrintMs >= 200) {
    selfTestPrintMs = now;
    const size_t i = SELF_TEST_MOTOR_INDEX;
    Serial.printf("M%u target=%+.1f rpm=%+.2f raw=%+.2f pwm=%+d fault=%d\n",
                  static_cast<unsigned>(i + 1), pid[i].targetRpm,
                  pid[i].measuredRpm, pid[i].rawRpm,
                  static_cast<int>(pid[i].pwm), pid[i].directionFault);
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  Serial.setTimeout(30);

  for (size_t i = 0; i < MOTOR_COUNT; ++i) {
    motors[i].mcpwm_begin();
    applyMotorPwm(i, 0);
    configureEncoder(i);
  }

  if (ENABLE_SERVOS) {
    servo1.attach(SERVO1_PIN, 500, 2500);
    servo2.attach(SERVO2_PIN, 500, 2500);
    setServoAngles(packetStatus[S1], packetStatus[S2]);
  }

  if (ENABLE_ULTRASONIC_STOP) {
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
  }

  const uint32_t now = millis();
  previousControlMs = now;
  previousUltrasonicMs = now;
  selfTestStageStartMs = now;
  selfTestPrintMs = now;
  lastValidCommandMs = now;

  if (PID_SELF_TEST_MODE) {
    stopAllMotors(now);
    setMotorTarget(SELF_TEST_MOTOR_INDEX, SELF_TEST_TARGETS[0], now, true);
    Serial.println("PID chassis: ONE-MOTOR SELF TEST MODE");
  } else {
    Serial.println("PID chassis firmware ready");
  }
}

void loop() {
  const uint32_t now = millis();
  updateUltrasonic(now);

  if (PID_SELF_TEST_MODE) updateSelfTest(now);
  else {
    processControlPacket(now);
    if (now - lastValidCommandMs > SERIAL_WATCHDOG_MS) {
      stopAllMotors(now);
      if (!watchdogReported) {
        Serial.println("TIMEOUT");
        watchdogReported = true;
      }
    }
  }

  updateAllPid(now);
  delay(1);
}
