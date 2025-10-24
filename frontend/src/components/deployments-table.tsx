import DeploymentStatusCircle from "@/components/deployment-status-circle";
import MessagePlatformImg from "@/components/message-platform-image";
import PaginationControls, {
  type PaginationControlsProps,
} from "@/components/pagination-controls";
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
import {
  MessagePlatformType,
  ModeratorDeploymentStatus,
  type DeploymentResponse,
} from "@/openapi";
import dayjs from "dayjs";
import { ArrowDown, ArrowUp, CirclePlus, Minus, Search } from "lucide-react";
import { useState, type FC } from "react";

const DeploymentsTable: FC<
  {
    deployments: DeploymentResponse[];
    onRowClick?: (id: DeploymentResponse) => void;
  } & PaginationControlsProps
> = ({
  deployments,
  page,
  hasNextPage,
  onNextPage,
  onPrevPage,
  onRowClick,
}) => {
  const [search, setSearch] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<
    ModeratorDeploymentStatus[]
  >(Object.values(ModeratorDeploymentStatus));
  const [selectedPlatforms, setSelectedPlatforms] = useState<
    MessagePlatformType[]
  >(Object.values(MessagePlatformType));
  const [sortOrder, setSortOrder] = useState<"asc" | "desc" | null>(null);

  const toggleStatus = (status: ModeratorDeploymentStatus) =>
    setSelectedStatuses((prev) => {
      if (prev.includes(status)) {
        if (prev.length > 1) {
          return prev.filter((p) => p !== status);
        }
        return prev;
      }

      return [...prev, status];
    });

  const togglePlatform = (platform: MessagePlatformType) =>
    setSelectedPlatforms((prev) => {
      if (prev.includes(platform)) {
        if (prev.length > 1) {
          return prev.filter((p) => p !== platform);
        }
        return prev;
      }

      return [...prev, platform];
    });

  const toggleSort = () =>
    setSortOrder((prev) =>
      prev === null ? "asc" : prev === "asc" ? "desc" : null,
    );

  const filtered = deployments
    .filter((d) =>
      search ? d.name.toLowerCase().includes(search.toLowerCase()) : true,
    )
    .filter((d) =>
      selectedStatuses.length > 0 ? selectedStatuses.includes(d.status) : true,
    )
    .filter((d) =>
      selectedPlatforms.length > 0
        ? selectedPlatforms.includes(d.platform)
        : true,
    );

  const sorted = [...filtered].sort((a, b) => {
    if (!sortOrder) return 0;
    const aTime = dayjs(a.created_at).unix();
    const bTime = dayjs(b.created_at).unix();
    return sortOrder === "asc" ? aTime - bTime : bTime - aTime;
  });

  const formatDate = (value: string) => dayjs(value).format("YY-MM-DD");

  return (
    <>
      {/* Filters */}
      <div className="mb-6 flex h-8 w-full gap-1">
        <div className="bg-secondary flex h-full w-fit items-center rounded-sm border p-1">
          <Search size={15} />
          <Input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="!focus:ring-0 h-full w-60 border-none !bg-transparent !shadow-none"
          />
        </div>

        {/* Status Filter */}
        <Popover>
          <PopoverTrigger asChild>
            <span className="bg-muted flex w-24 cursor-pointer items-center justify-center gap-2 rounded-sm border border-dashed border-neutral-600 text-sm font-semibold">
              <CirclePlus size={15} /> Status
            </span>
          </PopoverTrigger>
          <PopoverContent className="w-40 p-2">
            {Object.values(ModeratorDeploymentStatus).map((s) => (
              <label
                key={s}
                className="flex cursor-pointer items-center gap-2 p-1 text-sm"
              >
                <Input
                  type="checkbox"
                  checked={selectedStatuses.includes(s)}
                  onChange={() => toggleStatus(s)}
                  className="w-5"
                />
                <span className="capitalize">{s}</span>
              </label>
            ))}
          </PopoverContent>
        </Popover>

        {/* Platform Filter */}
        <Popover>
          <PopoverTrigger asChild>
            <span className="bg-muted flex w-28 cursor-pointer items-center justify-center gap-2 rounded-sm border border-dashed border-neutral-600 text-sm font-semibold">
              <CirclePlus size={15} /> Platform
            </span>
          </PopoverTrigger>
          <PopoverContent className="w-40 p-2">
            {Object.values(MessagePlatformType).map((p) => (
              <label
                key={p}
                className="flex cursor-pointer items-center gap-2 p-1 text-sm"
              >
                <Input
                  type="checkbox"
                  checked={selectedPlatforms.includes(p)}
                  onChange={() => togglePlatform(p)}
                  className="w-5"
                />
                <span className="capitalize">{p}</span>
              </label>
            ))}
          </PopoverContent>
        </Popover>
      </div>

      {/* Table */}
      <div className="border bg-transparent shadow-lg">
        <Table>
          <TableHeader className="bg-gray-50 dark:bg-neutral-800">
            <TableRow>
              <TableHead className="font-bold text-gray-700 dark:text-gray-200">
                Name
              </TableHead>
              <TableHead className="font-bold text-gray-700 dark:text-gray-200">
                Platform
              </TableHead>
              <TableHead className="font-bold text-gray-700 dark:text-gray-200">
                Status
              </TableHead>
              <TableHead
                onClick={toggleSort}
                className="cursor-pointer text-right font-bold text-gray-700 select-none dark:text-gray-200"
              >
                Date Created
                {sortOrder === "asc" && (
                  <ArrowUp size={14} className="ml-1 inline" />
                )}
                {sortOrder === "desc" && (
                  <ArrowDown size={14} className="ml-1 inline" />
                )}
                {sortOrder === null && (
                  <Minus size={14} className="ml-1 inline" />
                )}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((deployment) => (
              <TableRow
                key={deployment.deployment_id}
                onClick={() => onRowClick?.(deployment)}
                className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/40"
              >
                <TableCell className="font-medium">{deployment.name}</TableCell>
                <TableCell>
                  <MessagePlatformImg
                    platform={deployment.platform}
                    className="h-5 w-5"
                  />
                </TableCell>
                <TableCell>
                  <DeploymentStatusCircle status={deployment.status} />
                </TableCell>
                <TableCell className="text-muted-foreground text-right">
                  {formatDate(deployment.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <PaginationControls
        page={page}
        hasNextPage={hasNextPage}
        onPrevPage={onPrevPage}
        onNextPage={onNextPage}
      />
    </>
  );
};

export default DeploymentsTable;
