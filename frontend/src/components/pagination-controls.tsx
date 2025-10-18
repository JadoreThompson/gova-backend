import { ChevronLeft, ChevronRight } from "lucide-react";
import type { FC } from "react";
import { Button } from "./ui/button";

export interface PaginationControlsProps {
  page: number;
  hasNextPage: boolean;
  onPrevPage: () => void;
  onNextPage: () => void;
}

const PaginationControls: FC<PaginationControlsProps> = (props) => (
  <div className="flex h-full w-full items-center justify-end gap-3">
    <Button
      variant="ghost"
      onClick={() => (props.page > 1 ? props.onPrevPage() : null)}
      disabled={props.page <= 1}
      className="hover:!bg-transparent focus:!outline-none"
    >
      <ChevronLeft />
    </Button>

    <Button
      variant="ghost"
      onClick={() => (props.hasNextPage ? props.onNextPage() : null)}
      disabled={!props.hasNextPage}
      className="hover:!bg-transparent focus:!outline-none"
    >
      <ChevronRight />
    </Button>
  </div>
);

export default PaginationControls;
