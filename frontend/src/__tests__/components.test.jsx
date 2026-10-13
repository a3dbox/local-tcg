import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Binder } from "@/components/Binder";
import { ProgressBar, Chips } from "@/components/UI";
import { CardTile } from "@/components/CardTile";
import { describeRules } from "@/pages/CustomSets";

const cards = Array.from({ length: 20 }, (_, i) => ({ id: `s-${i + 1}`, localId: String(i + 1), name: `Card ${i + 1}`, image: null }));
const wrap = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

beforeAll(() => { Object.defineProperty(window, "innerWidth", { value: 500, writable: true }); });

test("binder shows 9 pockets per page and flips", () => {
  wrap(<Binder cards={cards} owned={{ "s-1": { normal: 2 } }} />);
  expect(screen.getByTestId("binder-page-indicator")).toHaveTextContent("Page 1 of 3");
  expect(screen.getByTestId("binder-pocket-s-1")).toBeInTheDocument();
  expect(screen.queryByTestId("binder-pocket-s-10")).toBeNull();
  expect(screen.getByTestId("binder-pocket-s-1")).toHaveTextContent("x2");
  expect(screen.getByTestId("binder-prev-button")).toBeDisabled();
  fireEvent.click(screen.getByTestId("binder-next-button"));
  expect(screen.getByTestId("binder-page-indicator")).toHaveTextContent("Page 2 of 3");
});

test("progress bar shows count and percent", () => {
  render(<ProgressBar label="Base" value={3} total={4} testid="pb" />);
  expect(screen.getByTestId("pb")).toHaveTextContent("3/4");
  expect(screen.getByTestId("pb")).toHaveTextContent("75%");
});

test("chips toggle selection", () => {
  const onChange = jest.fn();
  render(<Chips testid="c" options={["Fire", "Water"]} value="Fire" onChange={onChange} />);
  fireEvent.click(screen.getByTestId("c-fire"));
  expect(onChange).toHaveBeenCalledWith("");
  fireEvent.click(screen.getByTestId("c-water"));
  expect(onChange).toHaveBeenCalledWith("Water");
});

test("card tile shows GBP price, owned badge and duplicate counts", () => {
  wrap(<CardTile card={{ id: "a-1", name: "Pikachu", localId: "1" }} owned="2/5" price={3.2} />);
  expect(screen.getByTestId("card-tile-a-1")).toHaveTextContent("£3.20");
  expect(screen.getByTestId("owned-badge-a-1")).toHaveTextContent("2/5");
});

test("custom set rules description", () => {
  expect(describeRules({ type: "Darkness", category: "Pokemon" })).toBe("Darkness type · Pokemon");
  expect(describeRules({ dex: 7 })).toBe("Pokédex #7");
  expect(describeRules({})).toBe("Hand-picked cards");
});
