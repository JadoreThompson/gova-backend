import { useLogoutMutation } from "@/hooks/auth-hooks";
import { Bell, Bot, Box, FileText, LogOut, SendToBack } from "lucide-react";
import type { FC, ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import AuthGuard from "../auth-guard";
import SiteLogo from "../site-logo";
import ThemeToggle from "../theme-toggle";
import { Button } from "../ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
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

      <div className="flex items-center justify-center gap-6">
        <Bell size={15} />
        <ThemeToggle />
      </div>
    </header>
  );
};

const DashboardSidebar: FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const logoutMutation = useLogoutMutation();

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
    ["Deployments", "/deployments", Box],
    ["Moderators", "/moderators", Bot],
    ["Connections", "/connections", SendToBack],
  ] as const;

  return (
    <Sidebar className="border-transparent pt-12">
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

      <SidebarFooter>
        <Button
          onClick={handleLogout}
          variant="ghost"
          className="flex w-full items-center justify-start gap-2 hover:bg-red-100 dark:hover:bg-red-900/30"
          disabled={logoutMutation.isPending}
        >
          <LogOut size={16} />
          {logoutMutation.isPending ? "Logging out..." : "Logout"}
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
};

interface DashboardLayoutProps {
  children: ReactNode;
}

const DashboardLayout: FC<DashboardLayoutProps> = ({ children }) => {
  return (
    <AuthGuard>
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <DashboardSidebar />
          <div className="flex flex-1 flex-col pb-5">
            <Header />
            <div className="mt-12 min-h-200 w-full rounded-l-lg border-y-2 border-l-2 bg-neutral-100 p-4 dark:bg-neutral-900">
              <main>{children}</main>
            </div>
          </div>
        </div>
      </SidebarProvider>
    </AuthGuard>
  );
};

export default DashboardLayout;
