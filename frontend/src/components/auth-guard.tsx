import { useMeQueryAuthGuard } from "@/hooks/auth-hooks";
import { Loader2 } from "lucide-react";
import { useEffect, type FC, type ReactNode } from "react";
import { useNavigate } from "react-router";

const AuthGuard: FC<{ children: ReactNode }> = (props) => {
  const navigate = useNavigate();
  const meQuery = useMeQueryAuthGuard();

  useEffect(() => {
    if (meQuery.error) {
      const status = (meQuery.error as any).status;

      if (status === 401) {
        navigate("/login", { replace: true });
      }
    }
  }, [meQuery.error, navigate]);

  if (meQuery.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
        <span className="ml-2 text-sm text-gray-500">Checking session...</span>
      </div>
    );
  }

  if (meQuery.data) {
    return <>{props.children}</>;
  }

  return null;
};

export default AuthGuard;
