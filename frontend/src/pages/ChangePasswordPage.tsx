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
  useChangePasswordMutation,
  useVerifyActionMutation,
} from "@/hooks/auth-hooks";
import { VerifyActionAction } from "@/openapi";
import { Loader2 } from "lucide-react";
import { useState, type FC, type FormEvent } from "react";

type Step = "enter-password" | "verify-code";

const ChangePasswordPage: FC = () => {
  const [step, setStep] = useState<Step>("enter-password");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [code, setCode] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const changePasswordMutation = useChangePasswordMutation();
  const verifyActionMutation = useVerifyActionMutation();

  const handlePasswordSubmit = (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    if (password.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    changePasswordMutation
      .mutateAsync({ password })
      .then(() => {
        setSuccessMessage("A verification code has been sent to your email.");
        setStep("verify-code");
      })
      .catch((err) => {
        const message =
          err?.body?.detail ||
          "Failed to initiate password change. Please try again.";
        setErrorMessage(message);
      });
  };

  const handleCodeSubmit = (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    if (!code.trim()) {
      setErrorMessage("Please enter the verification code.");
      return;
    }

    verifyActionMutation
      .mutateAsync({ code, action: VerifyActionAction.change_password })
      .then(() => {
        setSuccessMessage("Your password has been changed successfully!");
        setCode("");
        setPassword("");
        setConfirmPassword("");
        setStep("enter-password");
      })
      .catch(() => {
        setErrorMessage("Invalid or expired verification code.");
      });
  };

  const renderPasswordStep = () => (
    <form onSubmit={handlePasswordSubmit}>
      <CardHeader>
        <CardTitle>Change Password</CardTitle>
        <CardDescription>
          Enter a new password. A verification code will be sent to your email
          to confirm the change.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="password">New Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            placeholder="********"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={changePasswordMutation.isPending}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm New Password</Label>
          <Input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            placeholder="********"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={changePasswordMutation.isPending}
            required
          />
        </div>
      </CardContent>
      <CardFooter>
        <Button
          type="submit"
          className="w-full"
          disabled={changePasswordMutation.isPending}
        >
          {changePasswordMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sending Code...
            </>
          ) : (
            "Continue"
          )}
        </Button>
      </CardFooter>
    </form>
  );

  const renderVerificationStep = () => (
    <form onSubmit={handleCodeSubmit}>
      <CardHeader>
        <CardTitle>Verify Your Action</CardTitle>
        <CardDescription>
          Enter the verification code sent to your email to finalize the
          password change.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="code">Verification Code</Label>
          <Input
            id="code"
            name="code"
            placeholder="Enter your code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={verifyActionMutation.isPending}
            required
          />
        </div>
        <Button
          variant="link"
          type="button"
          onClick={() => {
            setStep("enter-password");
            setErrorMessage("");
            setSuccessMessage("");
          }}
          className="h-auto p-0"
        >
          Want to use a different password?
        </Button>
      </CardContent>
      <CardFooter>
        <Button
          type="submit"
          className="w-full"
          disabled={verifyActionMutation.isPending}
        >
          {verifyActionMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Verifying...
            </>
          ) : (
            "Confirm Password Change"
          )}
        </Button>
      </CardFooter>
    </form>
  );

  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        {step === "enter-password"
          ? renderPasswordStep()
          : renderVerificationStep()}
        <div className="min-h-[20px] px-6 pb-4">
          {errorMessage && (
            <p className="text-destructive text-sm font-medium">
              {errorMessage}
            </p>
          )}
          {successMessage && !errorMessage && (
            <p className="text-sm font-medium text-green-600">
              {successMessage}
            </p>
          )}
        </div>
      </Card>
    </div>
  );
};

export default ChangePasswordPage;
