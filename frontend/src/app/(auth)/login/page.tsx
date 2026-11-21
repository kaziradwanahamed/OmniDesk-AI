"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Layers, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.login(email.trim(), password);
      router.push("/projects");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed.");
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-sm p-6">
      <div className="mb-6 flex flex-col items-center gap-2 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-fg">
          <Layers className="h-5 w-5" />
        </span>
        <h1 className="text-lg font-semibold text-primary">Welcome back</h1>
        <p className="text-sm text-secondary">
          Sign in to your OmniDesk AI workspace.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-3" noValidate>
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
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            disabled={submitting}
          />
        </div>
        {error ? <p className="text-xs text-danger">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Sign in
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-secondary">
        No account?{" "}
        <Link
          href="/register"
          className="font-medium text-accent hover:opacity-80"
        >
          Create one
        </Link>
      </p>
    </Card>
  );
}
