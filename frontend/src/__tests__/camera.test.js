import { frameStats, nextSteadyState, guideRect } from "@/components/camera";

const flat = (v, n = 48 * 66) => new Float32Array(n).fill(v);
const checker = (w = 48, h = 66) => Float32Array.from({ length: w * h }, (_, i) => (((i % w) + Math.floor(i / w)) % 2 ? 255 : 0));

test("frameStats measures motion and sharpness", () => {
  expect(frameStats(flat(10), 48, 66, null).motion).toBe(999);
  expect(frameStats(flat(10), 48, 66, flat(30)).motion).toBeCloseTo(20);
  expect(frameStats(flat(10), 48, 66, flat(10)).sharpness).toBe(0);
  expect(frameStats(checker(), 48, 66, null).sharpness).toBeGreaterThan(1000);
});

test("steady state fires once after enough still sharp frames, then waits for motion", () => {
  let s = { still: 0, armed: true };
  const still = { motion: 1, sharpness: 500 };
  s = nextSteadyState(s, still); expect(s.fire).toBe(false);
  s = nextSteadyState(s, still); expect(s.fire).toBe(false);
  s = nextSteadyState(s, still); expect(s.fire).toBe(true);
  s = nextSteadyState(s, still); expect(s.status).toBe("waiting"); expect(s.fire).toBe(false);
  s = nextSteadyState(s, { motion: 50, sharpness: 500 }); expect(s.status).toBe("moving"); expect(s.armed).toBe(true);
});

test("blurry frames never fire", () => {
  let s = { still: 0, armed: true };
  for (let i = 0; i < 5; i++) s = nextSteadyState(s, { motion: 1, sharpness: 5 });
  expect(s.status).toBe("blurry");
  expect(s.fire).toBe(false);
});

test("guideRect maps the on-screen frame into video pixels", () => {
  const video = { videoWidth: 1920, videoHeight: 1440, clientWidth: 480, clientHeight: 640 };
  const r = guideRect(video, 1);
  expect(r.sh).toBeCloseTo(1440 * 0.82, 0);
  expect(r.sw / r.sh).toBeCloseTo(63 / 88, 3);
  expect(r.sx + r.sw / 2).toBeCloseTo(960, 0);
  expect(guideRect({}, 1)).toBeNull();
});
