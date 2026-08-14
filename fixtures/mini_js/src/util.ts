/** TypeScript twin of the JS fixture; same free-path plumbing claim. */

export class Counter {
  constructor(private start: number = 0) {}

  next(): number {
    this.start += 1;
    return this.start;
  }
}

export async function loadConfig(name: string): Promise<string> {
  return `config:${name}`;
}
