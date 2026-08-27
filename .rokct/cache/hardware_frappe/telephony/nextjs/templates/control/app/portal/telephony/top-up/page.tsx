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
// telephony/frappe/src/templates/pages/top_up.html — enter an amount and
// hand off to the Paystack checkout.
//
// initiate_top_up (unchanged, still served by Frappe) returns
// `/paystack_checkout?token=<name>` — the FRAPPE checkout page path, which
// external Paystack wiring may rely on. This page does not change that
// contract: it parses the token out of the returned URL and routes to this
// SDK's own checkout page (/portal/telephony/checkout?token=...) instead.

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Wallet } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  getCustomerBalance,
  initiateTopUp,
} from "@/app/actions/portal/telephony";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
  }).format(value || 0);
}

export default function TopUpPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [balance, setBalance] = useState(0);
  const [amount, setAmount] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await getCustomerBalance();
        if (res?.status === "success") {
          setBalance(res.data || 0);
        } else if (res?.message) {
          toast.error(res.message);
        }
      } catch (error) {
        console.error("Error fetching balance:", error);
        toast.error("Failed to fetch balance");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function handleTopUp() {
    const value = parseFloat(amount);
    if (!value || value <= 0) {
      toast.error("Please enter a valid amount.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await initiateTopUp(value);
      if (res?.status === "success" && res.data?.checkout_url) {
        // The endpoint returns the transitional Frappe checkout path
        // (/paystack_checkout?token=...); extract the token and use this
        // SDK's checkout page.
        const token = new URLSearchParams(
          res.data.checkout_url.split("?")[1] || "",
        ).get("token");
        if (token) {
          router.push(
            `/portal/telephony/checkout?token=${encodeURIComponent(token)}`,
          );
          return;
        }
        toast.error("Checkout token missing from response.");
      } else {
        toast.error(res?.message || "Failed to initiate top-up.");
      }
    } catch (error) {
      console.error("Error initiating top-up:", error);
      toast.error("Failed to initiate top-up");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 max-w-xl">
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="icon">
          <Link href="/portal/telephony">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-3xl font-bold tracking-tight">
          Top Up Your Balance
        </h1>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Current Balance</CardTitle>
          <Wallet className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-4xl font-bold">{formatCurrency(balance)}</div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="amount">Amount to Top Up</Label>
          <Input
            id="amount"
            type="number"
            min="0"
            step="0.01"
            placeholder="Enter amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <Button onClick={handleTopUp} disabled={submitting}>
          {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {submitting ? "Processing..." : "Proceed to Payment"}
        </Button>
      </div>
    </div>
  );
}
