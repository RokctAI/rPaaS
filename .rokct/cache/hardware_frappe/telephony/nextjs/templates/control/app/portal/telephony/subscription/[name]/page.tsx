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
// telephony/frappe/src/www/telephony_portal_details.html — one
// subscription's details, SIP provisioning QR, lifecycle actions
// (cancel/restart) and PortaBilling call history. The Frappe page addressed
// the subscription as ?name=<id>; this page uses a dynamic route segment
// (/portal/telephony/subscription/[name]).

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import {
  cancelSubscription,
  getCallHistory,
  getSubscriptionDetails,
  restartSubscription,
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

export default function TelephonySubscriptionDetailsPage() {
  const params = useParams<{ name: string }>();
  const subscriptionName = decodeURIComponent(params.name);

  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [subscription, setSubscription] = useState<any | null>(null);
  const [callHistory, setCallHistory] = useState<any[]>([]);
  const [acting, setActing] = useState(false);

  const fetchSubscriptionDetails = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getSubscriptionDetails(subscriptionName);
      if (res?.status === "success") {
        setSubscription(res.data);
      } else {
        toast.error(res?.message || "Failed to load subscription details.");
      }
    } catch (error) {
      console.error("Error fetching subscription details:", error);
      toast.error("Failed to load subscription details");
    } finally {
      setLoading(false);
    }
  }, [subscriptionName]);

  const fetchCallHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await getCallHistory(subscriptionName);
      if (res?.status === "success") {
        setCallHistory(res.data || []);
      }
    } catch (error) {
      console.error("Error fetching call history:", error);
    } finally {
      setHistoryLoading(false);
    }
  }, [subscriptionName]);

  useEffect(() => {
    if (!subscriptionName) return;
    fetchSubscriptionDetails();
    fetchCallHistory();
  }, [subscriptionName, fetchSubscriptionDetails, fetchCallHistory]);

  async function handleCancel() {
    if (!confirm("Are you sure you want to cancel this subscription?")) return;
    setActing(true);
    try {
      const res = await cancelSubscription(subscriptionName);
      if (res?.status === "success") {
        toast.success("Subscription cancelled successfully.");
        fetchSubscriptionDetails();
      } else {
        toast.error(res?.message || "Failed to cancel subscription.");
      }
    } catch (error) {
      toast.error("Failed to cancel subscription");
    } finally {
      setActing(false);
    }
  }

  async function handleRestart() {
    if (!confirm("Are you sure you want to restart this subscription?")) return;
    setActing(true);
    try {
      const res = await restartSubscription(subscriptionName);
      if (res?.status === "success") {
        toast.success("Subscription restarted successfully.");
        fetchSubscriptionDetails();
      } else {
        toast.error(res?.message || "Failed to restart subscription.");
      }
    } catch (error) {
      toast.error("Failed to restart subscription");
    } finally {
      setActing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!subscription) {
    return (
      <div className="container mx-auto p-4 md:p-8">
        <p className="text-muted-foreground">Subscription not found.</p>
        <Button asChild variant="secondary" className="mt-4">
          <Link href="/portal/telephony">Back to Portal</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <Button asChild variant="ghost" size="icon">
            <Link href="/portal/telephony">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <h1 className="text-3xl font-bold tracking-tight">
            Subscription Details
          </h1>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Subscription: {subscription.name}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p>
              <strong>Plan:</strong> {subscription.plan}
            </p>
            <p className="flex items-center gap-2">
              <strong>Status:</strong>{" "}
              <Badge variant={statusVariant(subscription.status)}>
                {subscription.status}
              </Badge>
            </p>
            <p>
              <strong>Number of Lines:</strong> {subscription.number_of_lines}
            </p>
            <p>
              <strong>Assigned Number (DID):</strong>{" "}
              {subscription.did_number || "Not Assigned"}
            </p>
            <hr className="my-4" />
            <h3 className="font-semibold">SIP Credentials</h3>
            <p>
              <strong>Username:</strong> {subscription.sip_username}
            </p>
          </CardContent>
          <CardFooter>
            {subscription.status === "Active" && (
              <Button
                variant="destructive"
                onClick={handleCancel}
                disabled={acting}
              >
                Cancel Subscription
              </Button>
            )}
            {subscription.status === "Cancelled" && (
              <Button onClick={handleRestart} disabled={acting}>
                Restart Subscription
              </Button>
            )}
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Zoiper Softphone Provisioning</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            {subscription.qr_code && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={subscription.qr_code}
                alt="QR Code for SIP Provisioning"
                className="mx-auto"
              />
            )}
            <p className="mt-2 text-muted-foreground">
              Scan with your Zoiper app to automatically configure your
              account.
            </p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Call History</h2>
        {historyLoading ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading...
          </div>
        ) : callHistory.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date/Time</TableHead>
                <TableHead>From</TableHead>
                <TableHead>To</TableHead>
                <TableHead>Duration (sec)</TableHead>
                <TableHead>Cost</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {callHistory.map((call, index) => (
                <TableRow key={index}>
                  <TableCell>
                    {call.bill_time
                      ? format(new Date(call.bill_time), "MMM d, yyyy HH:mm")
                      : "-"}
                  </TableCell>
                  <TableCell>{call.cli}</TableCell>
                  <TableCell>{call.cld}</TableCell>
                  <TableCell>{call.billed_duration}</TableCell>
                  <TableCell>{formatCurrency(call.charged_amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-muted-foreground">
            No call history available for this subscription.
          </p>
        )}
      </div>
    </div>
  );
}
