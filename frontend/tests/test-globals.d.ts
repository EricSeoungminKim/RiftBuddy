declare module "node:assert/strict" {
  interface StrictAssert {
    equal(actual: unknown, expected: unknown, message?: string): void
    deepEqual(actual: unknown, expected: unknown, message?: string): void
  }

  const assert: StrictAssert
  export default assert
}

declare module "node:test" {
  type TestBody = () => void | Promise<void>
  type Test = (name: string, body: TestBody) => void

  const test: Test
  export default test
}
