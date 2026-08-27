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
// telephony/frappe/src/templates/pages/telephony_signup.html — the public
// telephony signup flow: choose a plan, enter details, pick an area code,
// confirm, provision. Plans and area codes are fetched through server
// actions running under the shell's system identity (the Frappe page
// rendered them with server-side website context); provisioning submits to
// this module's provision_new_service method (control:provision_new_service,
// registered by telephony/frappe/manifest.json).

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  getAvailableAreaCodes,
  getTelephonyPlans,
  provisionNewService,
} from "@/app/actions/portal/telephony";

interface TelephonyPlan {
  name: string;
  plan_name: string;
  cost: number;
  billing_cycle: string;
  is_per_seat_plan: 0 | 1;
  base_user_count: number;
}

export default function TelephonySignupPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState<TelephonyPlan[]>([]);
  const [areaCodes, setAreaCodes] = useState<string[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<TelephonyPlan | null>(null);
  const [lines, setLines] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  // User details
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [country, setCountry] = useState("");
  const [selectedAreaCode, setSelectedAreaCode] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [plansData, codesRes] = await Promise.all([
          getTelephonyPlans(),
          getAvailableAreaCodes(),
        ]);
        setPlans(plansData || []);
        if (codesRes?.status === "success") {
          setAreaCodes(codesRes.data || []);
        }
      } catch (error) {
        console.error("Error loading signup data:", error);
        toast.error("Could not load subscription plans.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function selectPlan(plan: TelephonyPlan) {
    setSelectedPlan(plan);
    setLines(plan.is_per_seat_plan ? 1 : plan.base_user_count || 1);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedPlan) return;
    if (!selectedAreaCode) {
      toast.error("Please select an area code for your phone number.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await provisionNewService({
        plan: selectedPlan.name,
        lines,
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        company_name: companyName,
        currency: "USD",
        country,
        industry: "Telecommunications",
        area_code: selectedAreaCode,
      });
      if (res?.status === "success") {
        toast.success(
          "Subscription created successfully! You will be redirected shortly.",
        );
        setTimeout(() => {
          router.push("/portal/telephony");
        }, 2000);
      } else {
        toast.error(res?.message || "An unknown error occurred.");
      }
    } catch (error) {
      console.error("Error creating subscription:", error);
      toast.error("Failed to create subscription");
    } finally {
      setSubmitting(false);
    }
  }

  const totalCost = selectedPlan
    ? selectedPlan.is_per_seat_plan
      ? (selectedPlan.cost * lines).toFixed(2)
      : selectedPlan.cost.toFixed(2)
    : "0.00";

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Subscribe to a Telephony Plan
        </h1>
        <p className="text-muted-foreground">
          Choose a plan that fits your needs. Pro plans are priced per line.
        </p>
      </div>

      {!selectedPlan ? (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Step 1: Choose a Plan</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan) => (
              <Card key={plan.name}>
                <CardHeader>
                  <CardTitle>{plan.plan_name}</CardTitle>
                  <CardDescription>
                    ${plan.cost} / {plan.billing_cycle}
                    {" — "}
                    {plan.is_per_seat_plan ? "per line" : "fixed"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button onClick={() => selectPlan(plan)}>
                    Select This Plan
                  </Button>
                </CardContent>
              </Card>
            ))}
            {plans.length === 0 && (
              <p className="text-muted-foreground">
                No telephony plans are currently available.
              </p>
            )}
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <h2 className="text-xl font-semibold">Step 2: Your Details</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="firstName">First Name</Label>
              <Input
                id="firstName"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">Last Name</Label>
              <Input
                id="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="companyName">Company Name</Label>
            <Input
              id="companyName"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="country">Country</Label>
            <Input
              id="country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password (min. 8 characters)</Label>
            <Input
              id="password"
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <h2 className="text-xl font-semibold">Step 3: Choose Your Number</h2>
          <div className="space-y-2">
            <Label htmlFor="areaCode">Select an Area Code</Label>
            <select
              id="areaCode"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={selectedAreaCode}
              onChange={(e) => setSelectedAreaCode(e.target.value)}
              required
            >
              <option value="" disabled>
                Please select one
              </option>
              {areaCodes.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
            <p className="text-sm text-muted-foreground">
              A phone number will be automatically assigned to you from this
              area.
            </p>
          </div>

          <h2 className="text-xl font-semibold">Step 4: Confirm Your Plan</h2>
          <div className="space-y-2">
            <Label htmlFor="plan">Selected Plan</Label>
            <Input id="plan" value={selectedPlan.plan_name} readOnly />
          </div>
          {selectedPlan.is_per_seat_plan ? (
            <div className="space-y-2">
              <Label htmlFor="lines">Number of Lines: {lines}</Label>
              <input
                id="lines"
                type="range"
                min={1}
                max={100}
                value={lines}
                onChange={(e) => setLines(parseInt(e.target.value, 10))}
                className="w-full"
              />
            </div>
          ) : null}
          <div className="rounded-md border bg-muted/50 p-4 text-sm">
            Total Cost: ${totalCost} / {selectedPlan.billing_cycle}
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {submitting ? "Subscribing..." : "Complete Subscription"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setSelectedPlan(null)}
            >
              Change Plan
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
