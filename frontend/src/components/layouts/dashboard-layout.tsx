import { useLogoutMutation, useMeQuery } from "@/hooks/auth-hooks";
import { useMeStore } from "@/stores/me-store";
import { Bot, FileText, LogOut, SendToBack } from "lucide-react";
import { useEffect, type FC, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import AuthGuard from "../auth-guard";
import SiteLogo from "../site-logo";
import { Button } from "../ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "../ui/sidebar";

const Header: FC = () => {
  return (
    <header className="bg-background/80 fixed top-0 left-0 z-50 flex h-12 w-full items-center justify-between p-2 backdrop-blur-sm">
      <div className="flex w-20 items-center justify-center">
        <SiteLogo />
      </div>
    </header>
  );
};

const DashboardSidebar: FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const logoutMutation = useLogoutMutation();

  const me = useMeStore((state) => state.data);
  const setMe = useMeStore((state) => state.setData);
  const meQuery = useMeQuery();

  useEffect(() => {
    if (!me && meQuery.data) {
      setMe(meQuery.data);
    }
  }, [me, meQuery.data, setMe]);

  const handleLogout = async () => {
    try {
      await logoutMutation.mutateAsync();
      navigate("/login", { replace: true });
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const menuItems = [
    ["Guidelines", "/guidelines", FileText],
    ["Moderators", "/moderators", Bot],
    ["Connections", "/connections", SendToBack],
  ] as const;

  return (
    <Sidebar className="border-transparent pt-12 pb-3">
      <SidebarHeader className="bg-background px-3">
        <Link
          to={"/profile"}
          className="hover:bg-secondary flex h-full w-full flex-row items-center gap-2 rounded-md p-1"
        >
          <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-md bg-red-500">
            <img
              src={`https://ui-avatars.com/api/?name=${me?.username ?? "User"}`}
              alt="Profile"
            />
          </div>
          <span className="text-sm font-semibold">{me?.username ?? ""}</span>
        </Link>
      </SidebarHeader>
      <SidebarContent className="bg-background">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map(([title, url, Icon]) => {
                const isActive = location.pathname === url;

                return (
                  <SidebarMenuItem key={title}>
                    <SidebarMenuButton asChild>
                      <Link
                        to={url}
                        className={`flex items-center gap-2 rounded-md px-3 py-2 transition-colors duration-200 ${
                          isActive
                            ? "bg-blue-500/15 font-medium text-blue-600 dark:text-blue-400"
                            : "text-neutral-700 hover:bg-blue-500/10 hover:text-blue-500 dark:text-neutral-300 dark:hover:text-blue-400"
                        } `}
                      >
                        <Icon
                          size={16}
                          className={`${isActive ? "text-blue-500 dark:text-blue-400" : ""}`}
                        />
                        {title}
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="bg-background">
        <Button
          onClick={handleLogout}
          variant="ghost"
          className="bg-secondary flex w-full items-center justify-start gap-2 hover:bg-red-100 dark:hover:bg-red-900/30"
          disabled={logoutMutation.isPending}
        >
          <LogOut size={16} />
          {logoutMutation.isPending ? "Logging out..." : "Logout"}
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
};

const DashboardLayout: FC<{
  children: ReactNode;
}> = (props) => {
  return (
    <AuthGuard>
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <DashboardSidebar />
          <div className="flex flex-1 flex-col pb-5">
            <Header />
            <div className="pt-12">
              <div
                className="w-full rounded-l-lg border-y-2 border-l-2 bg-neutral-100 p-4 dark:bg-neutral-900"
                style={{
                  minHeight: "calc(100vh - 5rem)",
                }}
              >
                <main>{props.children}</main>
              </div>
            </div>
          </div>
        </div>
      </SidebarProvider>
    </AuthGuard>
  );
};

export default DashboardLayout;
