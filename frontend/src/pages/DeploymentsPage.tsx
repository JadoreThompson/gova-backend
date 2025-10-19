import DeploymentStatusCircle from "@/components/deployment-status-circle";
import DashboardLayout from "@/components/layouts/dashboard-layout";
import MessagePlatformImg from "@/components/message-platform-image";
import PaginationControls from "@/components/pagination-controls";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDeploymentsQuery } from "@/hooks/deployments-hooks";
import { MessagePlatformType, ModeratorDeploymentStatus } from "@/openapi";
import dayjs from "dayjs";
import { CirclePlus, Search } from "lucide-react";
import { type FC, useState } from "react";
import { useNavigate } from "react-router";

export interface DeploymentResponse {
  deployment_id: string;
  moderator_id: string;
  platform: MessagePlatformType;
  name: string;
  conf: unknown;
  state: ModeratorDeploymentStatus;
  created_at: string;
}

export interface PaginatedResponseDeploymentResponse {
  page: number;
  size: number;
  has_next: boolean;
  data: DeploymentResponse[];
}

const DeploymentsFilters = () => {
  const [search, setSearch] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<
    ModeratorDeploymentStatus[]
  >([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<
    MessagePlatformType[]
  >([]);

  const statusOptions: ModeratorDeploymentStatus[] = [
    ModeratorDeploymentStatus.offline,
    ModeratorDeploymentStatus.pending,
    ModeratorDeploymentStatus.online,
  ];

  const toggleStatus = (value: ModeratorDeploymentStatus) => {
    setSelectedStatuses((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value],
    );
  };

  const togglePlatform = (value: MessagePlatformType) => {
    setSelectedPlatforms((prev) =>
      prev.includes(value) ? prev.filter((p) => p !== value) : [...prev, value],
    );
  };

  return (
    <div className="mb-6 flex h-8 w-full gap-1">
      {/* Search Input */}
      <div className="bg-secondary flex h-full w-fit items-center justify-center gap-1 rounded-sm border p-1">
        <Search size={15} />
        <Input
          type="text"
          name="prefix"
          id="prefix"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search..."
          className="!focus:ring-0 h-full w-60 border-none !bg-transparent !shadow-none !ring-0"
        />
      </div>

      {/* Status Popover */}
      <Popover>
        <PopoverTrigger asChild>
          <span className="bg-muted flex w-24 cursor-pointer items-center justify-center gap-2 rounded-sm border border-dashed border-neutral-600 text-sm font-semibold">
            <CirclePlus size={15} />
            Status
          </span>
        </PopoverTrigger>
        <PopoverContent className="w-40 p-2">
          <div className="flex flex-col gap-2">
            {statusOptions.map((status) => (
              <label
                key={status}
                className="text-foreground flex h-6 cursor-pointer items-center gap-2 p-1 text-sm"
              >
                <Input
                  type="checkbox"
                  checked={selectedStatuses.includes(status)}
                  onInput={() => toggleStatus(status)}
                  className="w-5"
                />
                <span className="capitalize">{status}</span>
              </label>
            ))}
          </div>
        </PopoverContent>
      </Popover>

      {/* Platform Popover */}
      <Popover>
        <PopoverTrigger asChild>
          <span className="bg-muted flex w-28 cursor-pointer items-center justify-center gap-2 rounded-sm border border-dashed border-neutral-600 text-sm font-semibold">
            <CirclePlus size={15} />
            Platform
          </span>
        </PopoverTrigger>
        <PopoverContent className="w-40 p-2">
          <div className="flex flex-col gap-2">
            {Object.values(MessagePlatformType).map((platform) => (
              <label
                key={platform}
                className="text-foreground flex h-7 cursor-pointer items-center justify-start gap-2 p-1 text-sm"
              >
                <Input
                  type="checkbox"
                  checked={selectedPlatforms.includes(platform)}
                  onInput={() => togglePlatform(platform)}
                  className="w-5"
                />
                <span className="capitalize">{platform}</span>
              </label>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
};

const DeploymentsPage: FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);

  const deploymentsQuery = useDeploymentsQuery({
    page,
  });

  const getPlatformImageSrc = (value: MessagePlatformType) => {
    switch (value) {
      case "discord":
        return "/src/assets/discord.png";
    }
  };

  const formatDate = (value: string) => dayjs(value).format("YY-MM-DD");

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <h4 className="text-xl font-semibold">Deployments</h4>
      </div>

      <DeploymentsFilters />
      <div className="border bg-transparent shadow-lg">
        <Table>
          <TableHeader className="bg-gray-50 dark:bg-neutral-800">
            <TableRow>
              <TableHead className="w-200 font-bold text-gray-700 dark:text-gray-200">
                Name
              </TableHead>
              <TableHead className="w-3 font-bold text-gray-700 dark:text-gray-200">
                Platform
              </TableHead>
              <TableHead className="font-bold text-gray-700 dark:text-gray-200">
                Status
              </TableHead>
              <TableHead className="text-right font-bold text-gray-700 dark:text-gray-200">
                Date Created
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(deploymentsQuery.data?.data ?? []).map((deployment) => (
              <TableRow
                key={deployment.deployment_id}
                onClick={() =>
                  navigate(`/deployment/${deployment.deployment_id}`)
                }
                className="transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50"
              >
                <TableCell className="font-medium text-gray-900 dark:text-gray-100">
                  {deployment.name || "Unnamed Deployment"}
                </TableCell>
                <TableCell className="text-muted-foreground capitalize">
                  {/* <img
                    src={getPlatformImageSrc(deployment.platform)}
                    alt=""
                    className="h-5 w-5"
                  /> */}
                  <MessagePlatformImg
                    platform={deployment.platform}
                    className="h-5 w-5"
                  />
                </TableCell>
                <TableCell>
                  <DeploymentStatusCircle status={deployment.status} />
                </TableCell>
                <TableCell className="text-right text-sm text-gray-500 dark:text-gray-400">
                  {formatDate(deployment.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <PaginationControls
        page={page}
        hasNextPage={deploymentsQuery.data?.has_next ?? false}
        onPrevPage={() => setPage((page) => page - 1)}
        onNextPage={() => setPage((page) => page + 1)}
      />
    </DashboardLayout>
  );
};

export default DeploymentsPage;
