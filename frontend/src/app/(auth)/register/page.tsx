"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Layers, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api-client";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        await api.me();
        if (active) router.replace("/projects");
      } catch {
        if (active) setChecking(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !password) {
      setError("Fill in every field to continue.");
      return;
    }
    if (password.length < 8) {
      setError("Use a password of at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.register(email.trim(), password, name.trim());
      router.push("/projects");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed.");
      setSubmitting(false);
    }
  }

  if (checking) {
    return <Loader2 className="h-6 w-6 animate-spin text-tertiary" />;
  }

  return (
    <Card className="w-full max-w-sm p-6">
      <div className="mb-6 flex flex-col items-center gap-2 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-fg">
          <Layers className="h-5 w-5" />
        </span>
        <h1 className="text-lg font-semibold text-primary">
          Create your workspace
        </h1>
        <p className="text-sm text-secondary">
          Start a project and bring your own provider keys.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-3" noValidate>
        <div className="space-y-1.5">
          <label htmlFor="name" className="text-xs font-medium text-secondary">
            Name
          </label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            disabled={submitting}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="email" className="text-xs font-medium text-secondary">
            Email
          </label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            disabled={submitting}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label
              htmlFor="password"
              className="text-xs font-medium text-secondary"
            >
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="8+ characters"
              disabled={submitting}
            />
          </div>
          <div className="space-y-1.5">
            <label
              htmlFor="confirm"
              className="text-xs font-medium text-secondary"
            >
              Confirm
            </label>
            <Input
              id="confirm"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Repeat password"
              disabled={submitting}
            />
          </div>
        </div>
        {error ? <p className="text-xs text-danger">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Create account
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-secondary">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-accent hover:opacity-80">
          Sign in
        </Link>
      </p>
    </Card>
  );
}
