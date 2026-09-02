import { NextResponse } from 'next/server';

export function serviceUnavailable(service: string, error: unknown) {
  console.error(`${service} unavailable:`, error);
  return NextResponse.json(
    { error: `${service} is unavailable` },
    { status: 503 }
  );
}

export function toNumber(value: unknown): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}
