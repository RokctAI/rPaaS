/*
 * Copyright (c) 2026 RokctAI
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

"use client";

// Next.js successor of the transitional Frappe web page
// telephony/frappe/src/templates/pages/telephony_portal.html — the
// customer-facing telephony portal landing (balance + subscriptions) for
// the headless-Frappe architecture.

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Phone, RefreshCw, Wallet } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  getCustomerBalance,
  getUserSubscriptions,
} from "@/app/actions/portal/telephony";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
  }).format(value || 0);
}

function statusVariant(status: string) {
  if (status === "Active") return "default" as const;
  if (status === "Cancelled") return "destructive" as const;
  return "secondary" as const;
}

export default function TelephonyPortalPage() {
  const [loading, setLoading] = useState(true);
  const [subscriptions, setSubscriptions] = useState<any[]>([]);
  const [balance, setBalance] = useState(0);

  async function loadData() {
    setLoading(true);
    try {
      const [subsRes, balanceRes] = await Promise.all([
        getUserSubscriptions(),
        getCustomerBalance(),
      ]);
      if (subsRes?.status === "success") {
        setSubscriptions(subsRes.data || []);
      } else if (subsRes?.message) {
        toast.error(subsRes.message);
      }
      if (balanceRes?.status === "success") {
        setBalance(balanceRes.data || 0);
      }
    } catch (error) {
      console.error("Error loading telephony portal:", error);
      toast.error("Failed to load telephony portal data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            My Telephony Portal
          </h1>
          <p className="text-muted-foreground">
            Manage your telephony subscriptions and balance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={loadData} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button asChild variant="secondary">
            <Link href="/portal/telephony/top-up">Top Up</Link>
          </Button>
        </div>
      </div>

      <Card className="max-w-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Balance</CardTitle>
          <Wallet className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(balance)}</div>
        </CardContent>
      </Card>

      <div>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Phone className="h-5 w-5" /> My Subscriptions
        </h2>
        {subscriptions.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {subscriptions.map((sub) => (
              <Card key={sub.name}>
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-lg">{sub.plan}</CardTitle>
                    <Badge variant={statusVariant(sub.status)}>
                      {sub.status}
                    </Badge>
                  </div>
                  <CardDescription>{sub.name}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button asChild className="w-full">
                    <Link
                      href={`/portal/telephony/subscription/${encodeURIComponent(
                        sub.name,
                      )}`}
                    >
                      Manage
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-8 text-center">
            <h3 className="text-lg font-medium">
              No active telephony subscriptions
            </h3>
            <p className="text-muted-foreground mt-2">
              Sign up for a plan to get started.
            </p>
          </Card>
        )}
        <div className="mt-6">
          <Button asChild>
            <Link href="/portal/telephony/signup">
              Sign Up for a New Plan
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
