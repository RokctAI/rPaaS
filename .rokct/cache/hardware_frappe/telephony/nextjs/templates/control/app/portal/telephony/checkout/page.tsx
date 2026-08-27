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
// telephony/frappe/src/templates/pages/paystack_checkout.html — the hosted
// Paystack checkout, addressed by ?token=<Integration Request name>.
//
// Boundary notes (headless migration):
// - handle_paystack_callback stays a Frappe-served endpoint (it is the
//   server-side confirmation/webhook); this page only INVOKES it after a
//   successful inline payment, exactly as the Frappe page did.
// - The Paystack-configured redirect/checkout URL still points at the
//   Frappe /paystack_checkout page; switching that external wiring to this
//   page is a separate, outward-facing decision.

import { Suspense, useEffect, useRef, useState } from "react";
import Script from "next/script";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import {
  getPaymentRequestDetails,
  handlePaystackCallback,
} from "@/app/actions/portal/telephony";

declare global {
  interface Window {
    PaystackPop?: {
      setup: (options: Record<string, unknown>) => { openIframe: () => void };
    };
  }
}

function PaystackCheckout() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [scriptReady, setScriptReady] = useState(false);
  const [status, setStatus] = useState<string>("Preparing your payment...");
  const started = useRef(false);

  useEffect(() => {
    if (!scriptReady || started.current) return;
    if (!token) {
      setStatus("No payment token provided.");
      toast.error("No payment token provided.");
      return;
    }
    started.current = true;

    (async () => {
      try {
        const res = await getPaymentRequestDetails(token);
        if (res?.status !== "success") {
          setStatus(res?.message || "Failed to load payment details.");
          toast.error(res?.message || "Failed to load payment details.");
          return;
        }
        const data = res.data;
        if (!window.PaystackPop) {
          setStatus("Payment library failed to load.");
          toast.error("Payment library failed to load.");
          return;
        }
        setStatus("Redirecting to Paystack...");
        const handler = window.PaystackPop.setup({
          key: data.public_key,
          email: data.customer_email,
          amount: data.amount * 100,
          currency: data.currency,
          ref: data.reference,
          callback: (response: { reference: string }) => {
            (async () => {
              const cb = await handlePaystackCallback(
                response.reference,
                token,
              );
              if (cb?.status === "success") {
                toast.success("Top-up successful!");
                router.push("/portal/telephony/top-up");
              } else {
                toast.error(cb?.message || "Payment confirmation failed.");
              }
            })();
          },
          onClose: () => {
            toast.warning("Transaction was not completed, window closed.");
          },
        });
        handler.openIframe();
      } catch (error) {
        console.error("Error processing payment:", error);
        setStatus("Failed to process payment.");
        toast.error("Failed to process payment");
      }
    })();
  }, [scriptReady, token, router]);

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 max-w-xl">
      <Script
        src="https://js.paystack.co/v1/inline.js"
        onLoad={() => setScriptReady(true)}
      />
      <h1 className="text-3xl font-bold tracking-tight">Pay with Paystack</h1>
      <div className="flex items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>{status}</span>
      </div>
    </div>
  );
}

export default function PaystackCheckoutPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[50vh] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <PaystackCheckout />
    </Suspense>
  );
}
