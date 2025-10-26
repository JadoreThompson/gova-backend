import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import { type FC, type ReactNode } from "react";
import { Link } from "react-router";

interface PricingCardProps {
  planType?: "free" | "pro" | "enterprise";
  title: string;
  description: string;
  price: string;
  features: readonly string[];
  cta?: ReactNode;
}

const PricingCard: FC<PricingCardProps> = (props) => {
  return (
    <div
      className={cn(
        "mx-auto w-full max-w-sm transition-transform duration-300",
        props.planType === "pro" && "scale-[1.03] rounded-xl bg-blue-400 p-1",
      )}
    >
      {props.planType === "pro" && (
        <div className="mb-1 text-center text-sm font-semibold text-blue-900">
          Recommended
        </div>
      )}
      <Card
        className="flex flex-col gap-2 shadow-gray-500/20"
        style={{
          boxShadow:
            props.planType === "pro"
              ? "1px 1px 12px 1px rgba(0, 0, 0, 0.5)"
              : "",
        }}
      >
        <CardHeader>
          <h3 className="text-2xl font-semibold">{props.title}</h3>
          <p className="text-muted-foreground mb-3">{props.description}</p>
          <div className="border-b pb-5">
            <span className="mr-1 text-3xl font-bold">{props.price}</span>
            <span className="text-muted-foreground text-sm">/month</span>
          </div>
        </CardHeader>

        <CardContent className="pb-8">
          <p className="mb-2 font-semibold">What's included:</p>
          <ul className="space-y-2">
            {props.features.map((feature, index) => (
              <li key={index} className="flex items-start gap-3">
                <Check size={20} className="mt-[2px] text-green-500" />
                <span className="text-sm">{feature}</span>
              </li>
            ))}
          </ul>
        </CardContent>

        <CardFooter>
          {props.cta ?? <Button className="w-full">Get Started</Button>}
        </CardFooter>
      </Card>
    </div>
  );
};

const PricingPage: FC = () => {
  const sendToPaymentLink = () => {};
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Fixed-positioned inner section */}
      <div className="bg-secondary fixed inset-0 m-2 flex flex-col items-center justify-center overflow-y-auto rounded-md border p-4 sm:m-4 sm:p-6 md:p-10 lg:m-8">
        <h2 className="mb-3 text-center text-2xl font-bold sm:text-3xl md:text-4xl">
          Plans and Pricing
        </h2>
        <p className="text-muted-foreground mb-10 max-w-2xl text-center text-sm sm:text-base">
          Choose a plan that fits your needs. Upgrade anytime as your team
          grows.
        </p>

        {/* Responsive Pricing Grid */}
        <div className="grid w-full grid-cols-1 gap-6 px-2 sm:grid-cols-2 sm:gap-8 sm:px-0 md:max-w-6xl lg:grid-cols-3">
          {(
            [
              {
                planType: "free",
                title: "Free Plan",
                description: "Basic features for personal use",
                price: "$0",
                features: [
                  "Up to 1,000 messages moderated",
                  "Basic moderation tools",
                  "Email support",
                ],
              },
              {
                planType: "pro",
                title: "Pro Plan",
                description: "Advanced features for professionals",
                price: "$29",
                features: [
                  "Up to 100,000 messages moderated",
                  "Advanced moderation tools",
                  "Priority email support",
                ],
              },
              {
                planType: "enterprise",
                title: "Enterprise Plan",
                description: "All features for large organizations",
                price: "Contact us",
                features: [
                  "Unlimited messages moderated",
                  "All moderation tools",
                  "Dedicated support",
                ],
              },
            ] as const
          ).map((config) => (
            <PricingCard
              key={config.title}
              planType={config.planType}
              title={config.title}
              description={config.description}
              price={config.price}
              features={config.features}
              cta={
                config.planType === "enterprise" ? (
                  <Link to="#" className="w-full">
                    <Button className="w-full">Contact Us</Button>
                  </Link>
                ) : config.planType === "pro" ? (
                  <Link
                    to={
                      import.meta.env.VITE_HTTP_BASE_URL +
                      "/payments/payment-link"
                    }
                    className="w-full"
                  >
                    <Button className="w-full">Get Started</Button>
                  </Link>
                ) : (
                  <Link to="/login" className="w-full">
                    <Button className="w-full">Get Started</Button>
                  </Link>
                )
              }
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default PricingPage;
