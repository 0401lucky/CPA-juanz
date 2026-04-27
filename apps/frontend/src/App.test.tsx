import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "./App";


beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: {
          "Content-Type": "application/json"
        }
      });
    })
  );
});

describe("App", () => {
  test("公开首页展示 Gemini 捐献入口和管理码入口", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    expect(
      screen.getByRole("heading", { name: "Gemini 凭证捐献站" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Google 授权捐献" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "上传 JSON 凭证" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "输入管理码" })
    ).toBeInTheDocument();
  });

  test("我的凭证页展示追加上传和记录列表区域", async () => {
    render(
      <MemoryRouter initialEntries={["/my"]}>
        <App />
      </MemoryRouter>
    );

    expect(
      screen.getByRole("heading", { name: "我的凭证" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "继续追加 Gemini 凭证" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "当前记录" })
    ).toBeInTheDocument();
    expect(await screen.findByText("当前还没有记录。")).toBeInTheDocument();
  });

  test("管理员页展示审核工作台入口", () => {
    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByText("审核工作台")).toBeInTheDocument();
    expect(screen.getByText("待审核队列")).toBeInTheDocument();
  });
});
