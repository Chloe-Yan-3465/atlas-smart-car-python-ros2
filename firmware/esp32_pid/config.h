#pragma once

#include <Arduino.h>
#include "driver/pcnt.h"

// Group 19 wiring profile. Recalibrate signs and counts on the actual chassis.
constexpr size_t MOTOR_COUNT = 4;
constexpr uint8_t MOTOR_A_PINS[MOTOR_COUNT] = {12, 14, 16, 18};
constexpr uint8_t MOTOR_B_PINS[MOTOR_COUNT] = {13, 15, 17, 19};
constexpr gpio_num_t ENCODER_A_PINS[MOTOR_COUNT] = {GPIO_NUM_25, GPIO_NUM_32, GPIO_NUM_34, GPIO_NUM_36};
constexpr gpio_num_t ENCODER_B_PINS[MOTOR_COUNT] = {GPIO_NUM_26, GPIO_NUM_33, GPIO_NUM_35, GPIO_NUM_39};
constexpr int8_t ENCODER_SIGN[MOTOR_COUNT] = {1, 1, 1, 1};
constexpr float COUNTS_PER_WHEEL_REV[MOTOR_COUNT] = {99000.0f, 99000.0f, 99000.0f, 99000.0f};

constexpr uint8_t SERVO1_PIN = 21;
constexpr uint8_t SERVO2_PIN = 22;
constexpr bool ENABLE_SERVOS = true;
constexpr bool ENABLE_ULTRASONIC_STOP = false;
constexpr uint8_t TRIG_PIN = 4;
constexpr uint8_t ECHO_PIN = 5;
constexpr float STOP_DISTANCE_CM = 10.0f;
constexpr uint32_t ULTRASONIC_INTERVAL_MS = 100;

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint32_t SERIAL_WATCHDOG_MS = 2000;
constexpr uint32_t CONTROL_INTERVAL_MS = 20;
constexpr float MAX_TARGET_RPM = 300.0f;
constexpr int16_t STARTUP_PWM = 85;
constexpr int16_t MAX_PWM_OUTPUT = 120;
constexpr uint32_t STARTUP_KICK_MS = 200;
constexpr float RPM_FILTER_ALPHA = 0.25f;
constexpr float KP = 0.45f;
constexpr float KI = 0.80f;
constexpr float KD = 0.001f;
constexpr float FEED_FORWARD_PWM_PER_RPM = 0.36f;

constexpr bool PID_SELF_TEST_MODE = false;
constexpr size_t SELF_TEST_MOTOR_INDEX = 0;
constexpr uint32_t SELF_TEST_STAGE_MS = 5000;

