"use client";
import { useContext, useSyncExternalStore } from "react";
import { StudentState, privateKeys } from "@/components/auth/student-provider";
import { dataMode } from "@/services/config";
import { emptyStudent } from "@/services/student";
const listeners = new Set<() => void>();
function subscribe(listener: () => void) {
  listeners.add(listener);
  const handler = () => listener();
  window.addEventListener("storage", handler);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", handler);
  };
}
export function usePersistentState<T>(
  key: string,
  initial: T,
  validate?: (value: unknown) => value is T,
): [T, (value: T | ((previous: T) => T)) => void | Promise<void>] {
  const cloud = useContext(StudentState);
  const raw = useSyncExternalStore(
    subscribe,
    () => {
      try {
        return window.localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    () => null,
  );
  function parse(value: string | null): T {
    try {
      const parsed: unknown = value === null ? initial : JSON.parse(value);
      return !validate || validate(parsed) ? (parsed as T) : initial;
    } catch {
      return initial;
    }
  }
  const state = parse(raw);
  if (dataMode === "api" && privateKeys.has(key)) {
    const fallback: unknown =
      key === "student-profile"
        ? emptyStudent
        : key === "financial-plan"
          ? initial
          : key === "financial-scenario"
            ? null
            : key === "new-user"
              ? false
              : [];
    const current = (
      !cloud?.loading && cloud?.workspace
        ? (cloud.values[key] ?? fallback)
        : fallback
    ) as T;
    return [
      current,
      (value) => {
        const next =
          typeof value === "function"
            ? (value as (previous: T) => T)(current)
            : value;
        if (
          ["financial-plan", "financial-scenario"].includes(key) &&
          cloud?.user
        ) {
          cloud.draft(key, next);
          return;
        }
        if (!cloud) return;
        const promise = cloud.update(key, next);
        void promise.catch(() => {}); // Global cloud error remains visible; callers may also await.
        return promise;
      },
    ];
  }
  function update(value: T | ((previous: T) => T)) {
    try {
      const previous = parse(window.localStorage.getItem(key));
      const next =
        typeof value === "function"
          ? (value as (previous: T) => T)(previous)
          : value;
      window.localStorage.setItem(key, JSON.stringify(next));
      listeners.forEach((listener) => listener());
    } catch {
      window.alert(
        "Local storage is unavailable. Allow browser storage to save demo preferences.",
      );
    }
  }
  return [state, update];
}
export const isStringList = (v: unknown): v is string[] =>
  Array.isArray(v) && v.every((x) => typeof x === "string");
