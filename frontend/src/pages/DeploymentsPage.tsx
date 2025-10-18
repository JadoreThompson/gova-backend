import DeploymentStatusCircle from "@/components/deployment-status-circle";
import DashboardLayout from "@/components/layouts/dashboard-layout";
import { Button } from "@/components/ui/button";
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
import { MessagePlatformType, ModeratorDeploymentStatus } from "@/openapi";
import dayjs from "dayjs";
import {
  ChevronLeft,
  ChevronRight,
  CirclePlus,
  Loader2,
  Search,
} from "lucide-react";
import { type FC, useMemo, useState } from "react";
import { useNavigate } from "react-router";

// Mocking Tanstack Query structure for the hook
// In a real project, this dependency would be imported: import { useQuery } from "@tanstack/react-query";
interface MockQueryReturn<T> {
  data: T | undefined;
  isLoading: boolean;
  isError: boolean;
  isFetching: boolean;
}

// --- ORVAL TYPE SIMULATION (for local testing) ---
// Since we can't import types from '@/openapi' here and use the mock, we define the required types locally.
// export enum ModeratorDeploymentState {
//   offline = "offline",
//   pending = "pending",
//   online = "online",
// }

// export enum MessagePlatformType {
//   discord = "discord",
// }

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
// --- END ORVAL TYPE SIMULATION ---

// --- MOCK DATA IMPLEMENTATION ---

const mockDiscordConfig = {
  guild_id: 123456789,
  allowed_channels: [101, 102, 103],
  allowed_actions: [
    { type: "ban", reason: "Violation of rules" },
    { type: "mute", reason: "Spamming" },
  ],
};

const createMockDeployment = (
  id: number,
  state: ModeratorDeploymentStatus,
  name: string,
): DeploymentResponse => ({
  deployment_id: `dep-${id.toString().padStart(3, "0")}`,
  moderator_id: `mod-${id.toString().padStart(3, "0")}`,
  platform: MessagePlatformType.discord,
  name: name,
  conf: mockDiscordConfig,
  state: state,
  created_at: new Date(Date.now() - id * 86400000).toISOString(), // Days ago
});

const MOCK_DEPLOYMENTS_LIST: DeploymentResponse[] = [
  createMockDeployment(1, ModeratorDeploymentStatus.online, "Discord Bot V1.2"),
  createMockDeployment(
    2,
    ModeratorDeploymentStatus.online,
    "Community Mod 2.0",
  ),
  createMockDeployment(3, ModeratorDeploymentStatus.offline, "Archive 2023"),
  createMockDeployment(
    4,
    ModeratorDeploymentStatus.pending,
    "Test Deployment 4",
  ),
  createMockDeployment(5, ModeratorDeploymentStatus.online, "Main Server Mod"),
  createMockDeployment(
    6,
    ModeratorDeploymentStatus.offline,
    "Debug Instance X",
  ),
  createMockDeployment(
    7,
    ModeratorDeploymentStatus.online,
    "High Traffic Guard",
  ),
  createMockDeployment(
    8,
    ModeratorDeploymentStatus.pending,
    "Scheduled Update",
  ),
  createMockDeployment(9, ModeratorDeploymentStatus.online, "Discord Bot V1.3"),
  createMockDeployment(10, ModeratorDeploymentStatus.offline, "Stale Instance"),
  createMockDeployment(
    11,
    ModeratorDeploymentStatus.online,
    "Backup Moderator",
  ),
  createMockDeployment(
    12,
    ModeratorDeploymentStatus.pending,
    "New Feature Rollout",
  ),
  createMockDeployment(
    13,
    ModeratorDeploymentStatus.online,
    "Beta Channel Monitor",
  ),
  createMockDeployment(14, ModeratorDeploymentStatus.offline, "Legacy System"),
  createMockDeployment(15, ModeratorDeploymentStatus.online, "Deployment 15"),
];

const MOCK_PAGE_SIZE = 5;
const MOCK_DELAY = 700;

const getMockDeploymentPage = (
  page: number,
  size: number = MOCK_PAGE_SIZE,
): PaginatedResponseDeploymentResponse => {
  const startIndex = (page - 1) * size;
  const endIndex = startIndex + size;

  const data = MOCK_DEPLOYMENTS_LIST.slice(startIndex, endIndex);
  const has_next = endIndex < MOCK_DEPLOYMENTS_LIST.length;

  return {
    page,
    size,
    has_next,
    data,
  };
};

/**
 * MOCK implementation of useDeploymentsQuery for development/mocking purposes.
 * Simulates API fetching and pagination delay.
 */
function useDeploymentsQuery(params: {
  page: number;
}): MockQueryReturn<PaginatedResponseDeploymentResponse> {
  const page = params.page ?? 1;

  // We use a simple local state to simulate fetching and caching
  const [mockData, setMockData] = useState<
    PaginatedResponseDeploymentResponse | undefined
  >(undefined);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);

  useMemo(() => {
    if (page < 1) return;

    const fetchData = async () => {
      setIsFetching(true);
      try {
        // Simulate network delay
        await new Promise((resolve) => setTimeout(resolve, MOCK_DELAY));
        const data = getMockDeploymentPage(page);
        setMockData(data);
      } catch (error) {
        // Should handle error state simulation here if needed
        console.error("Mock query error:", error);
      } finally {
        setIsLoading(false);
        setIsFetching(false);
      }
    };

    // On page change, simulate refetching/loading
    setIsFetching(true);
    fetchData();
  }, [page]);

  return {
    data: mockData,
    isLoading: isLoading, // Initial loading state
    isError: false, // Simple mock, assume no error
    isFetching: isFetching, // Loading state on subsequent pages
  };
}
// --- END MOCK HOOK IMPLEMENTATION ---

/** Renders the pagination controls for the table. */
interface TablePaginationProps {
  page: number;
  hasNext: boolean;
  isFetching: boolean;
  setPage: (page: number) => void;
}

const TablePagination: FC<TablePaginationProps> = ({
  page,
  hasNext,
  isFetching,
  setPage,
}) => {
  const nextDisabled = !hasNext || isFetching;
  const prevDisabled = page <= 1 || isFetching;

  return (
    <div className="flex items-center justify-between space-x-2 px-2 py-4">
      <div className="text-muted-foreground text-sm">
        Showing page {page} of{" "}
        {Math.ceil(MOCK_DEPLOYMENTS_LIST.length / MOCK_PAGE_SIZE)}
      </div>
      <div className="flex space-x-2">
        <Button
          variant="ghost"
          size="sm"
          className="!bg-transparent shadow-none"
          onClick={() => setPage(page - 1)}
          disabled={prevDisabled}
        >
          <ChevronLeft
            className={`mr-1 h-4 w-4 ${nextDisabled ? "text-muted-foreground" : "text-primary"}`}
          />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="!bg-transparent"
          onClick={() => setPage(page + 1)}
          disabled={nextDisabled}
        >
          <ChevronRight
            className={`ml-1 h-4 w-4 ${nextDisabled ? "text-muted-foreground" : "text-primary"}`}
          />
        </Button>
      </div>
    </div>
  );
};

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

  const platformOptions: MessagePlatformType[] = [
    MessagePlatformType.discord,
    // Add others if needed, e.g., MessagePlatformType.slack, etc.
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
    <div className="mb-6 flex h-7 w-full gap-1">
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
            {platformOptions.map((platform) => (
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
  const [currentPage, setCurrentPage] = useState(1);

  // NOTE: In a real environment, replace this mock hook with:
  // const { data, isLoading, isError, isFetching } = useDeploymentsQuery({ page: currentPage });
  const { data, isLoading, isError, isFetching } = useDeploymentsQuery({
    page: currentPage,
  });

  const deployments = data?.data || [];
  const hasNext = data?.has_next || false;

  const handleSetPage = (page: number) => {
    setCurrentPage(Math.max(1, page));
  };

  const getPlatformImageSrc = (value: MessagePlatformType) => {
    switch (value) {
      case "discord":
        return "/src/assets/discord.png";
    }
  };

  const formatDate = (value: string) => dayjs(value).format("YY-MM-DD");

  if (isError) {
    return (
      <DashboardLayout>
        <h4 className="mb-6 text-xl font-semibold">Deployments</h4>
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-600">
          Error loading deployments. Please try again later.
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <h4 className="text-xl font-semibold">Deployments</h4>
        {/* Future action button */}
        {/* <Button>Deploy New</Button> */}
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
            {(isLoading || isFetching) && deployments.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-blue-600 dark:text-blue-400" />
                  <p className="text-muted-foreground mt-2 text-sm">
                    Loading deployments...
                  </p>
                </TableCell>
              </TableRow>
            )}

            {!isLoading && deployments.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-muted-foreground h-24 text-center"
                >
                  No deployments found.
                </TableCell>
              </TableRow>
            )}

            {deployments.map((deployment: DeploymentResponse) => (
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
                  <img
                    src={getPlatformImageSrc(deployment.platform)}
                    alt=""
                    className="h-5 w-5"
                  />
                </TableCell>
                <TableCell>
                  <DeploymentStatusCircle status={deployment.state} />
                </TableCell>
                <TableCell className="text-right text-sm text-gray-500 dark:text-gray-400">
                  {/* {deployment.created_at} */}
                  {formatDate(deployment.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination Controls */}
      {/* Show pagination if we are not in initial loading phase and we have data or potential next pages */}
      {!isLoading && (deployments.length > 0 || currentPage > 1 || hasNext) && (
        <TablePagination
          page={currentPage}
          hasNext={hasNext}
          isFetching={isFetching}
          setPage={handleSetPage}
        />
      )}
    </DashboardLayout>
  );
};

export default DeploymentsPage;
