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
  useChangeUsernameMutation,
  useVerifyActionMutation,
} from "@/hooks/auth-hooks";
import { Loader2 } from "lucide-react";
import { useState, type FC, type FormEvent } from "react";
import { VerifyActionAction } from "@/openapi";

type Step = "enter-username" | "verify-code";

const ChangeUsernamePage: FC = () => {
  const [step, setStep] = useState<Step>("enter-username");
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const changeUsernameMutation = useChangeUsernameMutation();
  const verifyActionMutation = useVerifyActionMutation();

  const handleUsernameSubmit = (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    if (username.trim().length < 3) {
      setErrorMessage("Username must be at least 3 characters long.");
      return;
    }

    changeUsernameMutation
      .mutateAsync({ username })
      .then(() => {
        setSuccessMessage(
          "A verification code has been sent to your email.",
        );
        setStep("verify-code");
      })
      .catch((err) => {
        const message =
          err?.body?.detail ||
          "Failed to initiate username change. Please try again.";
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
      .mutateAsync({ code, action: VerifyActionAction.change_username })
      .then(() => {
        setSuccessMessage("Your username has been changed successfully!");
        // Reset form state
        setCode("");
        setUsername("");
        setStep("enter-username");
      })
      .catch(() => {
        setErrorMessage("Invalid or expired verification code.");
      });
  };

  const renderUsernameStep = () => (
    <form onSubmit={handleUsernameSubmit}>
      <CardHeader>
        <CardTitle>Change Username</CardTitle>
        <CardDescription>
          Enter a new username. A verification code will be sent to your email to confirm the change.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="username">New Username</Label>
          <Input
            id="username"
            name="username"
            placeholder="Your new username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={changeUsernameMutation.isPending}
            required
          />
        </div>
      </CardContent>
      <CardFooter>
        <Button
          type="submit"
          className="w-full"
          disabled={changeUsernameMutation.isPending}
        >
          {changeUsernameMutation.isPending ? (
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
          Enter the verification code sent to your email to finalize the username change.
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
            setStep("enter-username");
            setErrorMessage("");
            setSuccessMessage("");
          }}
          className="h-auto p-0"
        >
          Want to use a different username?
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
            "Confirm Username Change"
          )}
        </Button>
      </CardFooter>
    </form>
  );

  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        {step === "enter-username"
          ? renderUsernameStep()
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

export default ChangeUsernamePage;