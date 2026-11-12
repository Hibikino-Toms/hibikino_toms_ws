#pragma once

#include <stdint.h>

// Hardware-independent, non-blocking NC-switch homing. The caller applies
// outputPwm(), zeros the encoder exactly on entry to DONE, and services its
// independent serial watchdog. An initially open switch must close during a
// bounded release before its next opening may establish home.
class RailHoming {
 public:
  enum Phase { IDLE, RELEASE, SEEK, CONTACT, DONE, FAULT, CANCELLED };
  struct Config {
    int retractPwm;
    uint32_t timeoutMs;
    uint32_t debounceMs;
    uint32_t releaseMaxCounts;
    uint32_t seekMaxCounts;
    uint32_t progressTimeoutMs;
  };

  void start(uint32_t id, const Config &config, uint32_t now,
             int32_t encoder, bool switchOpen) {
    id_ = id;
    cfg_ = config;
    started_ = progressAt_ = now;
    origin_ = progressEncoder_ = encoder;
    releaseDelta_ = 0;
    stable_ = false;
    error_ = "NONE";
    phase_ = switchOpen ? RELEASE : SEEK;
    output_ = switchOpen ? -cfg_.retractPwm : cfg_.retractPwm;
  }

  void update(uint32_t now, int32_t encoder, bool switchOpen) {
    if (!active()) return;
    if (now - started_ >= cfg_.timeoutMs) return fail("TIMEOUT");
    if (phase_ == RELEASE) {
      if (distance(encoder, origin_) > cfg_.releaseMaxCounts)
        return fail("SWITCH_DID_NOT_CLOSE");
      // Also observe one encoder count so even a power-on at the switch can
      // establish encoder polarity. Release remains bounded by max counts.
      const bool clear = !switchOpen && distance(encoder, origin_) >= 1;
      output_ = clear ? 0 : -cfg_.retractPwm;
      if (!clear) {
        stable_ = false;
      } else if (!stable_) {
        stable_ = true;
        stableAt_ = now;
      } else if (now - stableAt_ >= cfg_.debounceMs) {
        releaseDelta_ = static_cast<int64_t>(encoder) - origin_;
        phase_ = SEEK;
        origin_ = progressEncoder_ = encoder;
        progressAt_ = now;
        stable_ = false;
        output_ = cfg_.retractPwm;
      }
    } else {
      if (distance(encoder, origin_) > cfg_.seekMaxCounts)
        return fail("SEEK_TRAVEL_LIMIT");
      if (switchOpen) {
        // Raw switch opening always stops the rail before debounce completes.
        output_ = 0;
        if (phase_ != CONTACT) {
          phase_ = CONTACT;
          stableAt_ = now;
        } else if (now - stableAt_ >= cfg_.debounceMs) {
          if (retractEncoderSign(encoder) == 0) {
            // Contact reached before a full encoder count: verify by backing
            // off once rather than accepting an unknown encoder direction.
            phase_ = RELEASE;
            origin_ = progressEncoder_ = encoder;
            progressAt_ = now;
            releaseDelta_ = 0;
            stable_ = false;
            output_ = -cfg_.retractPwm;
          } else {
            phase_ = DONE;
          }
        }
      } else {
        phase_ = SEEK;
        output_ = cfg_.retractPwm;
      }
    }
    if (output_ != 0) {
      if (encoder != progressEncoder_) {
        progressEncoder_ = encoder;
        progressAt_ = now;
      } else if (now - progressAt_ >= cfg_.progressTimeoutMs) {
        fail("NO_ENCODER_PROGRESS");
      }
    } else {
      progressAt_ = now;
      progressEncoder_ = encoder;
    }
  }

  void cancel(const char *reason = "STOP") {
    if (active()) {
      phase_ = CANCELLED;
      error_ = reason;
    }
    output_ = 0;
  }
  bool active() const { return phase_ == RELEASE || phase_ == SEEK || phase_ == CONTACT; }
  Phase phase() const { return phase_; }
  int outputPwm() const { return output_; }
  uint32_t id() const { return id_; }
  const char *error() const { return error_; }
  int retractEncoderSign(int32_t encoder) const {
    int64_t delta = static_cast<int64_t>(encoder) - origin_;
    if (delta == 0) delta = -releaseDelta_;
    return delta > 0 ? 1 : delta < 0 ? -1 : 0;
  }
  void invalidate(const char *reason) { fail(reason); }
  const char *phaseName() const {
    switch (phase_) {
      case RELEASE: return "RELEASE";
      case SEEK: return "SEEK";
      case CONTACT: return "CONTACT";
      case DONE: return "DONE";
      case FAULT: return "FAULT";
      case CANCELLED: return "CANCELLED";
      default: return "IDLE";
    }
  }

 private:
  void fail(const char *reason) { phase_ = FAULT; output_ = 0; error_ = reason; }
  static uint64_t distance(int32_t a, int32_t b) {
    int64_t d = static_cast<int64_t>(a) - static_cast<int64_t>(b);
    return static_cast<uint64_t>(d < 0 ? -d : d);
  }
  Phase phase_ = IDLE;
  Config cfg_ = {};
  uint32_t id_ = 0, started_ = 0, stableAt_ = 0, progressAt_ = 0;
  int32_t origin_ = 0, progressEncoder_ = 0;
  int64_t releaseDelta_ = 0;
  bool stable_ = false;
  int output_ = 0;
  const char *error_ = "NONE";
};
