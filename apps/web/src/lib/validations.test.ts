import { describe, expect, it } from "vitest";
import { fieldErrors, loginSchema } from "@/lib/validations";

describe("loginSchema", () => {
  it("requires a valid email and password length", () => {
    const errors = fieldErrors(loginSchema, {
      email: "not-an-email",
      password: "short",
    });
    expect(errors.email).toMatch(/valid email/i);
    expect(errors.password).toMatch(/at least 8/i);
  });

  it("accepts valid credentials", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "password123",
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty email", () => {
    const errors = fieldErrors(loginSchema, {
      email: "   ",
      password: "password123",
    });
    expect(errors.email).toBeTruthy();
  });
});
