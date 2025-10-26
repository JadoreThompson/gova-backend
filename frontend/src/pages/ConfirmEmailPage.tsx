import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    useRequestEmailVerificationMutation,
    useVerifyEmailMutation,
} from "@/hooks/auth-hooks";
import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState, type FC, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router";

const RESEND_COOLDOWN_SECONDS = 30;

const ConfirmEmailPage: FC = () => {
  const location = useLocation();
  const [tokenInput, setTokenInput] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendMessage, setResendMessage] = useState("");

  const queryParamsRef = useRef(new URLSearchParams(location.search));
  const navigate = useNavigate();

  const verifyEmailMutation = useVerifyEmailMutation();
  const requestEmailVerificationMutation =
    useRequestEmailVerificationMutation();

  useEffect(() => {
    const token = queryParamsRef.current.get("token");
    if (token) {
      setTokenInput(token);
    }
  }, [queryParamsRef]);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => {
        setResendCooldown(resendCooldown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage("");
    setResendMessage("");

    if (!tokenInput.trim()) {
      setErrorMessage("Please enter a verification code.");
      return;
    }

    verifyEmailMutation
      .mutateAsync({ code: tokenInput })
      .then(() =>
        navigate("/login", {
          state: {
            message: "Email verified successfully! You can now log in.",
          },
        }),
      )
      .catch(() =>
        setErrorMessage("The provided code is invalid or has expired."),
      );
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || requestEmailVerificationMutation.isPending)
      return;

    setErrorMessage("");
    setResendMessage("");

    requestEmailVerificationMutation
      .mutateAsync()
      .then(() => {
        setResendMessage(
          "A new verification code has been sent to your email.",
        );
        setResendCooldown(RESEND_COOLDOWN_SECONDS);
      })
      .catch(() => {
        setErrorMessage(
          "Failed to resend. Please ensure you are logged in if you have an existing account.",
        );
      });
  };

  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <form onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle className="text-2xl">Confirm Your Email</CardTitle>
            <CardDescription>
              Enter the verification code sent to your email address.
            </CardDescription>
          </CardHeader>
          <CardContent className="py-3">
            <div className="space-y-2">
              <Label htmlFor="code">Verification Code</Label>
              <Input
                id="code"
                placeholder="Paste your code here"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                disabled={verifyEmailMutation.isPending}
                required
              />
            </div>

            <div className="mt-2 min-h-[20px]">
              {errorMessage && (
                <p className="text-destructive text-sm font-medium">
                  {errorMessage}
                </p>
              )}
              {resendMessage && (
                <p className="text-sm font-medium text-green-600">
                  {resendMessage}
                </p>
              )}
            </div>

            <div className="text-sm">
              Didn't receive a code?
              <Button
                variant={"link"}
                type="button"
                onClick={handleResend}
                disabled={
                  resendCooldown > 0 ||
                  requestEmailVerificationMutation.isPending
                }
                className="disabled:text-muted-foreground h-auto p-1 font-medium disabled:cursor-not-allowed"
              >
                {requestEmailVerificationMutation.isPending
                  ? "Sending..."
                  : resendCooldown > 0
                    ? `Resend again in ${resendCooldown}s`
                    : "Resend email"}
              </Button>
            </div>
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={verifyEmailMutation.isPending}
            >
              {verifyEmailMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                "Confirm Email"
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};

export default ConfirmEmailPage;
