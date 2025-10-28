import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRegisterMutation } from "@/hooks/auth-hooks";
import { useRedirectAuthenticated } from "@/hooks/redirect-authenticated";
import { Loader2 } from "lucide-react";
import { useRef, useState, type FC, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";

const RegisterPage: FC = () => {
  useRedirectAuthenticated({ to: "/moderators" });

  const location = useLocation();
  const navigate = useNavigate();
  const registerMutation = useRegisterMutation();

  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
  });
  const [errorMessage, setErrorMessage] = useState<string>("");

  const queryParamsRef = useRef(new URLSearchParams(location.search));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage("");

    registerMutation
      .mutateAsync(formData)
      .then(() =>
        navigate(
          queryParamsRef.current.size
            ? `/confirm-email?${queryParamsRef.current.toString()}`
            : "/confirm-email",
        ),
      )
      .catch((err: any) => {
        const message = err?.error || "Registration failed. Please try again.";
        setErrorMessage(message);
      });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-neutral-900">
      <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-800">
        <h2 className="mb-6 text-center text-2xl font-semibold">
          Create an Account
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium" htmlFor="username">
              Username
            </label>
            <Input
              id="username"
              name="username"
              type="text"
              placeholder="Your unique username"
              value={formData.username}
              onChange={handleChange}
              disabled={registerMutation.isPending}
              required
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-sm font-medium" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="your-email@example.com"
              value={formData.email}
              onChange={handleChange}
              disabled={registerMutation.isPending}
              required
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-sm font-medium" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="********"
              value={formData.password}
              onChange={handleChange}
              disabled={registerMutation.isPending}
              required
              className="mt-1"
            />
          </div>

          {errorMessage && (
            <p className="text-sm text-red-500">{errorMessage}</p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={registerMutation.isPending}
          >
            {registerMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Account...
              </>
            ) : (
              "Create Account"
            )}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-300">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
