import DashboardLayout from "@/components/layouts/dashboard-layout";
import PaginationControls, {
  type PaginationControlsProps,
} from "@/components/pagination-controls";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetClose, SheetContent } from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateGuidelineMutation,
  useGuidelinesQuery,
} from "@/hooks/guidelines-hooks";
import dayjs from "dayjs";
import { ArrowDown, ArrowUp, Minus, PlusCircle, Search, X } from "lucide-react";
import { useState, type FC } from "react";

interface GuidelineResponse {
  guideline_id: string;
  name: string;
  text: string;
  created_at: string;
  topics: string[];
}

const BADGE_COLORS = [
  "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300",
  "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300",
  "bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300",
  "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300",
  "bg-pink-100 text-pink-800 border-pink-200 dark:bg-pink-900/30 dark:text-pink-300",
  "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300",
];
const randomBadgeClass = () =>
  BADGE_COLORS[Math.floor(Math.random() * BADGE_COLORS.length)];

const GuidelinesTable: FC<
  {
    guidelines: GuidelineResponse[];
    onRowClick: (g: GuidelineResponse) => void;
  } & PaginationControlsProps
> = (props) => {
  const [sortOrder, setSortOrder] = useState<"asc" | "desc" | null>(null);

  const sortedGuidelines = (() => {
    if (sortOrder === "asc") {
      return [...props.guidelines].sort(
        (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      );
    }

    if (sortOrder === "desc") {
      return [...props.guidelines].sort(
        (a, b) => dayjs(b.created_at).unix() - dayjs(a.created_at).unix(),
      );
    }

    return props.guidelines;
  })();

  const toggleSort = () => {
    setSortOrder((prev) =>
      prev === null ? "asc" : prev === "asc" ? "desc" : null,
    );
  };

  return (
    <>
      <Table className="border-1">
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
              Topics
            </TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {sortedGuidelines.map((g) => (
            <TableRow
              key={g.guideline_id}
              onClick={() => props.onRowClick(g)}
              className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/40"
            >
              <TableCell className="font-medium">{g.name}</TableCell>
              <TableCell className="text-muted-foreground text-sm">
                {dayjs(g.created_at).format("YYYY-MM-DD HH:mm")}
              </TableCell>
              <TableCell className="flex flex-wrap gap-1 py-3">
                {g.topics.slice(0, 3).map((topic) => (
                  <span
                    key={topic}
                    className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${randomBadgeClass()}`}
                  >
                    {topic}
                  </span>
                ))}
                {g.topics.length > 3 && (
                  <span className="text-muted-foreground text-xs">
                    +{g.topics.length - 3} more
                  </span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <PaginationControls
        page={props.page}
        hasNextPage={props.hasNextPage}
        onPrevPage={props.onPrevPage}
        onNextPage={props.onNextPage}
      />
    </>
  );
};

const ViewGuidelineSheet: FC<{
  guideline: GuidelineResponse | null;
  onClose: () => void;
}> = ({ guideline, onClose }) => (
  <Sheet open={!!guideline} onOpenChange={onClose}>
    <SheetContent side="right" className="w-[400px] px-5 pt-10 sm:w-[480px]">
      {guideline && (
        <>
          <SheetClose className="absolute top-0 right-0 focus:!outline-none">
            <X size={17} />
          </SheetClose>

          <h4 className="font-semibold underline">{guideline.name}</h4>

          <div className="mt-6 space-y-4">
            <h6 className="text-muted-foreground text-sm font-semibold">
              Topics
            </h6>
            <div className="flex flex-wrap gap-2">
              {guideline.topics.map((topic) => (
                <span
                  key={topic}
                  className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${randomBadgeClass()}`}
                >
                  {topic}
                </span>
              ))}
            </div>

            <h6 className="text-muted-foreground text-sm font-semibold">
              Description
            </h6>
            <p className="text-foreground text-sm font-medium">
              {guideline.text}
            </p>
          </div>
        </>
      )}
    </SheetContent>
  </Sheet>
);

const AddGuidelineSheet: FC<{
  open: boolean;
  onClose: (open: boolean) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
}> = (props) => {
  const [newName, setNewName] = useState("");
  const [newText, setNewText] = useState("");

  return (
    <Sheet open={props.open} onOpenChange={props.onClose}>
      <SheetContent side="right" className="w-[400px] px-5 pt-10 sm:w-[480px]">
        <SheetClose className="absolute top-0 right-0 focus:!outline-none">
          <X size={17} />
        </SheetClose>

        <form onSubmit={props.onSubmit}>
          <h4 className="mb-4 font-semibold underline">Add New Guideline</h4>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Guideline Name</label>
              <Input
                placeholder="Enter guideline name"
                value={newName}
                name="name"
                onChange={(e) => setNewName(e.target.value)}
                className="mt-1"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Guideline Text</label>
              <Textarea
                placeholder="Paste or write your guideline here..."
                value={newText}
                name="text"
                onChange={(e) => setNewText(e.target.value)}
                className="mt-1 min-h-[150px]"
              />
            </div>

            <div className="flex justify-end pt-4">
              <Button type="submit" className="w-full border-1">
                Save Guideline
              </Button>
            </div>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
};

const GuidelinesPage: FC = () => {
  const [selectedGuideline, setSelectedGuideline] =
    useState<GuidelineResponse | null>(null);
  const [addSheetOpen, setAddSheetOpen] = useState(false);
  const [searchValue, setSearchValue] = useState<string>("");
  const [page, setPage] = useState<number>(1);

  const guidelinesQuery = useGuidelinesQuery({
    page,
    search: searchValue.trim(),
  });
  const createGuidelineMutation = useCreateGuidelineMutation();

  const handleGuidelineSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const formData = Object.fromEntries(
      new FormData(e.currentTarget).entries(),
    ) as { name: string; text: string };

    const name = formData.name.trim();
    const text = formData.text.trim();

    if (!name.trim() || !text.trim()) return;

    createGuidelineMutation
      .mutateAsync({ name, text })
      .then(() => guidelinesQuery.refetch());

    setAddSheetOpen(false);
  };

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <h4 className="text-xl font-semibold">Guidelines</h4>
      </div>

      <div className="mb-6 flex h-10 w-full items-center justify-between">
        <Button
          variant="outline"
          className="h-full text-sm"
          onClick={() => setAddSheetOpen(true)}
        >
          <PlusCircle />
          Add Guideline
        </Button>

        <div className="bg-secondary flex h-full w-auto items-center rounded-md border p-1">
          <Search size={20} />
          <Input
            type="text"
            placeholder="Search..."
            onChange={(e) => setSearchValue(e.target.value)}
            className="border-none !bg-transparent focus:!ring-0"
          />
        </div>
      </div>

      <GuidelinesTable
        guidelines={guidelinesQuery.data?.data ?? []}
        onRowClick={setSelectedGuideline}
        page={page}
        hasNextPage={guidelinesQuery.data?.has_next ?? false}
        onNextPage={() =>
          guidelinesQuery.data!.has_next ? setPage((p) => p + 1) : null
        }
        onPrevPage={() => (page > 1 ? setPage((p) => p - 1) : null)}
      />

      <ViewGuidelineSheet
        guideline={selectedGuideline}
        onClose={() => setSelectedGuideline(null)}
      />

      <AddGuidelineSheet
        open={addSheetOpen}
        onClose={setAddSheetOpen}
        onSubmit={handleGuidelineSubmit}
      />
    </DashboardLayout>
  );
};

export default GuidelinesPage;
