import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
    if (token) setTokenInput(token);
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
      .then(() => {
        const next = queryParamsRef.current.get("next");
        if (next?.trim()) {
          next.startsWith("/") ? navigate(next) : window.open(next);
        } else {
          navigate("/moderators");
        }
      })
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
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-neutral-900">
      <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-800">
        <h2 className="mb-6 text-center text-2xl font-semibold">
          Confirm Your Email
        </h2>
        <p className="mb-4 text-center text-sm text-gray-600 dark:text-gray-300">
          Enter the verification code sent to your email address.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium" htmlFor="code">
              Verification Code
            </label>
            <Input
              id="code"
              placeholder="Paste your code here"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              disabled={verifyEmailMutation.isPending}
              required
              className="mt-1"
            />
          </div>

          {errorMessage && (
            <p className="text-sm text-red-500">{errorMessage}</p>
          )}
          {resendMessage && (
            <p className="text-sm text-green-600">{resendMessage}</p>
          )}

          <div className="text-sm">
            Didn't receive a code?{" "}
            <Button
              variant="link"
              type="button"
              onClick={handleResend}
              disabled={
                resendCooldown > 0 || requestEmailVerificationMutation.isPending
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
        </form>
      </div>
    </div>
  );
};

export default ConfirmEmailPage;
