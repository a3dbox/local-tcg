import { formatErr, gbp, usd, eur, cardImg, logoImg, vLabel } from "@/lib/api";

test("currency formatters", () => {
  expect(gbp(1.5)).toBe("£1.50");
  expect(gbp(null)).toBe("—");
  expect(usd(2)).toBe("$2.00");
  expect(eur(0.456)).toBe("€0.46");
});

test("image helpers", () => {
  expect(cardImg("https://x/sv/1")).toBe("https://x/sv/1/low.webp");
  expect(cardImg("https://x/sv/1", "high")).toBe("https://x/sv/1/high.webp");
  expect(cardImg(null)).toBeNull();
  expect(logoImg("https://x/logo")).toBe("https://x/logo.webp");
});

test("variant labels", () => {
  expect(vLabel("reverse")).toBe("Reverse Holo");
  expect(vLabel("firstEdition")).toBe("1st Edition");
  expect(vLabel("custom")).toBe("custom");
});

test("formatErr handles strings, validation arrays and fallbacks", () => {
  expect(formatErr({ response: { data: { detail: "Nope" } } })).toBe("Nope");
  expect(formatErr({ response: { data: { detail: [{ msg: "a" }, { msg: "b" }] } } })).toBe("a b");
  expect(formatErr({ message: "Network" })).toBe("Network");
  expect(formatErr({})).toMatch(/Something went wrong/);
});
