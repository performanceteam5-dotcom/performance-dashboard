"""
15초 앰비언트 BGM 생성 - 테크 프로모 스타일
구성: 부드러운 신스 패드 + 미니멀 비트
"""
import wave
import struct
import math

SAMPLE_RATE = 44100
DURATION = 15.5  # 약간 여유 있게
NUM_SAMPLES = int(SAMPLE_RATE * DURATION)


def sine(t, freq, amp=1.0, phase=0.0):
    return amp * math.sin(2 * math.pi * freq * t + phase)


def generate_sample(t):
    s = 0.0

    # === PAD LAYER: 부드러운 코드 패드 (Cm9 분위기) ===
    # 루트 C3
    s += sine(t, 130.81, 0.12)
    # E♭3
    s += sine(t, 155.56, 0.10)
    # G3
    s += sine(t, 196.00, 0.09)
    # B♭3
    s += sine(t, 233.08, 0.08)
    # D4 (9th)
    s += sine(t, 293.66, 0.06)

    # === HARMONIC SHIMMER: 옥타브 위 배음 (subtle) ===
    s += sine(t, 261.63, 0.04)   # C4
    s += sine(t, 392.00, 0.03)   # G4

    # === SUB BASS: 느린 서브 (8마디 루프) ===
    # C1 → G1 패턴 (7.5초 주기)
    phase_bass = t % 7.5
    bass_freq = 65.41 if phase_bass < 3.75 else 98.00  # C2 → G2
    s += sine(t, bass_freq, 0.18) * 0.5

    # === PULSE: 미니멀 리듬 테이크 (120 BPM = 0.5s) ===
    beat_t = t % 0.5
    if beat_t < 0.02:
        pulse_env = 1.0 - (beat_t / 0.02)
        s += sine(t, 440, 0.08) * pulse_env  # 킥 느낌 하이 톤

    # 오프비트 하이햇 느낌 (0.25초마다)
    hihat_t = t % 0.25
    if hihat_t < 0.01:
        hihat_env = 1.0 - (hihat_t / 0.01)
        # 노이즈 대신 고주파 배음
        s += sine(t, 8000, 0.015) * hihat_env
        s += sine(t, 10000, 0.010) * hihat_env

    # === ATMOSPHERE: 느린 LFO 모듈레이션 ===
    lfo = 0.5 + 0.5 * sine(t, 0.15)  # 6.7초 주기 흔들림
    s *= (0.85 + 0.15 * lfo)

    # === FADE IN / FADE OUT ===
    fade_in = min(t / 1.0, 1.0)       # 1초 페이드인
    fade_out = min((DURATION - t) / 1.0, 1.0)  # 마지막 1초 페이드아웃
    s *= fade_in * fade_out

    # 클리핑 방지
    return max(-0.9, min(0.9, s))


print("BGM 생성 중...")
samples = []
for i in range(NUM_SAMPLES):
    t = i / SAMPLE_RATE
    val = generate_sample(t)
    samples.append(int(val * 32767))

with wave.open(
    r"C:\Users\MADUP\Desktop\clade_0514\claude-code-promo\public\bgm.wav", "w"
) as f:
    f.setnchannels(1)          # mono
    f.setsampwidth(2)          # 16-bit
    f.setframerate(SAMPLE_RATE)
    for s in samples:
        f.writeframes(struct.pack("<h", s))

print(f"완료: bgm.wav ({DURATION}초, {SAMPLE_RATE}Hz, 16-bit mono)")
