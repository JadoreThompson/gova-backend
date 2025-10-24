import DashboardLayout from "@/components/layouts/dashboard-layout";
import MessagePlatformImg from "@/components/message-platform-image";
import PaginationControls from "@/components/pagination-controls";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetClose, SheetContent } from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useGuidelinesQuery } from "@/hooks/guidelines-hooks";
import {
  useCreateModeratorMutation,
  useModeratorsQuery,
} from "@/hooks/moderators-hooks";
import { formatDate } from "@/lib/utils/utils";
import dayjs from "dayjs";
import { ArrowDown, ArrowUp, Minus, Search, X } from "lucide-react";
import { useEffect, useState, type FC } from "react";
import { useNavigate } from "react-router";

interface ModeratorGuideline {
  guideline_id: string;
  name: string;
}

const AddModeratorSheet: FC<{
  open: boolean;
  onClose: (open: boolean) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
}> = (props) => {
  const [newName, setNewName] = useState("");
  const [selectedGuidelineId, setSelectedGuidelineId] = useState("");

  const guidelinesQuery = useGuidelinesQuery({ page: 1, search: "" });

  const guidelines: ModeratorGuideline[] = (
    (guidelinesQuery.data?.data as ModeratorGuideline[]) ?? []
  ).filter((g) => !!g.guideline_id && !!g.name);

  useEffect(() => {
    if (!props.open) {
      setNewName("");
      setSelectedGuidelineId("");
    }
  }, [props.open]);

  return (
    <Sheet open={props.open} onOpenChange={props.onClose}>
      <SheetContent side="right" className="w-[400px] px-5 pt-10 sm:w-[480px]">
        <SheetClose className="absolute top-0 right-0 focus:!outline-none">
          <X size={17} />
        </SheetClose>

        <form onSubmit={props.onSubmit}>
          <h4 className="mb-4 font-semibold underline">Create New Moderator</h4>

          <div className="space-y-4">
            <div>
              <label htmlFor="moderator-name" className="text-sm font-medium">
                Moderator Name
              </label>
              <Input
                id="name"
                placeholder="Enter moderator name"
                value={newName}
                name="name"
                onChange={(e) => setNewName(e.target.value)}
                className="mt-1"
              />
            </div>

            <div>
              <label htmlFor="guideline-select" className="text-sm font-medium">
                Base Guideline
              </label>
              <Select
                name="guideline_id"
                value={selectedGuidelineId}
                onValueChange={setSelectedGuidelineId}
              >
                <SelectTrigger id="guideline-select" className="mt-1 w-full">
                  <SelectValue placeholder="Select a guideline..." />
                </SelectTrigger>
                <SelectContent>
                  {guidelinesQuery.isLoading && (
                    <div className="p-2 text-center text-sm">
                      Loading guidelines...
                    </div>
                  )}
                  {guidelines.length === 0 && !guidelinesQuery.isLoading && (
                    <div className="p-2 text-center text-sm">
                      No guidelines found.
                    </div>
                  )}
                  {guidelines.map((g) => (
                    <SelectItem key={g.guideline_id} value={g.guideline_id}>
                      {g.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex justify-end pt-4">
              <Button type="submit" className="w-full border-1">
                Create Moderator
              </Button>
            </div>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
};

const ModeratorsPage: FC = () => {
  const navigate = useNavigate();

  const [page, setPage] = useState(1);
  const [name, setName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc" | null>(null);

  const moderatorsQuery = useModeratorsQuery({ page, name });
  const createModeratorMutation = useCreateModeratorMutation();

  const handleModeratorSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const formData = Object.fromEntries(
      new FormData(e.currentTarget).entries(),
    ) as { guideline_id: string; name: string };
    if (!formData.name.trim()) return;

    createModeratorMutation
      .mutateAsync(formData)
      .then((rsp) => navigate(`/moderators/${rsp.moderator_id}`));
    setShowCreate(false);
  };

  const toggleSort = () => {
    setSortOrder((prev) =>
      prev === null ? "asc" : prev === "asc" ? "desc" : null,
    );
  };

  const sortedModerators = (() => {
    const mods = moderatorsQuery.data?.data ?? [];
    if (sortOrder === "asc") {
      return [...mods].sort(
        (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      );
    }
    if (sortOrder === "desc") {
      return [...mods].sort(
        (a, b) => dayjs(b.created_at).unix() - dayjs(a.created_at).unix(),
      );
    }
    return mods;
  })();

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <h4 className="text-xl font-semibold">Moderators</h4>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div className="bg-secondary flex h-fit w-fit items-center rounded-md border p-1">
          <Search size={20} />
          <Input
            type="text"
            placeholder="Search..."
            onChange={(e) => setName(e.currentTarget.value.trim())}
            className="h-7 w-50 border-none !bg-transparent focus:!ring-0"
          />
        </div>
        <Button onClick={() => setShowCreate(true)} variant={"outline"}>
          Create Moderator
        </Button>
      </div>

      <div className="border bg-transparent shadow-sm">
        <Table>
          <TableHeader className="bg-gray-50 dark:bg-neutral-800">
            <TableRow>
              <TableHead className="font-bold text-gray-700 dark:text-gray-200">
                Name
              </TableHead>
              <TableHead
                onClick={toggleSort}
                className="flex cursor-pointer items-center gap-1 font-bold text-gray-700 select-none dark:text-gray-200"
              >
                Created At
                {sortOrder === "asc" && <ArrowUp size={14} />}
                {sortOrder === "desc" && <ArrowDown size={14} />}
                {sortOrder === null && <Minus size={14} />}
              </TableHead>
              <TableHead className="font-bold text-gray-700 dark:text-gray-200">
                Deployments
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedModerators.map((mod) => (
              <TableRow
                key={mod.moderator_id}
                onClick={() => navigate(`/moderators/${mod.moderator_id}`)}
                className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/40"
              >
                <TableCell className="font-medium">{mod.name}</TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {formatDate(mod.created_at)}
                </TableCell>
                <TableCell className="flex flex-wrap gap-1 py-3">
                  {mod.deployment_platforms.map((pl) => (
                    <MessagePlatformImg
                      key={pl}
                      platform={pl}
                      className="h-5 w-5"
                    />
                  ))}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <PaginationControls
        page={page}
        hasNextPage={moderatorsQuery.data?.has_next ?? false}
        onNextPage={() => setPage((p) => p + 1)}
        onPrevPage={() => setPage((p) => p - 1)}
      />

      <AddModeratorSheet
        open={showCreate}
        onClose={setShowCreate}
        onSubmit={handleModeratorSubmit}
      />
    </DashboardLayout>
  );
};

export default ModeratorsPage;
