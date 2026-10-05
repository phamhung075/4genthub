import React from "react";
import { Search } from "lucide-react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Checkbox } from "./ui/checkbox";
import { Separator } from "./ui/separator";
import { Input } from "./ui/input";
import { Task } from "../api";

interface AgentAssignmentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | null;
  onClose: () => void;
  onAssign: (seats: string[]) => void;
  availableSeats: string[]; // Seat keys as assignees (@seat_key)
  availableSeatsError?: boolean; // The seats could not be loaded
  saving?: boolean;
}

export const AgentAssignmentDialog: React.FC<AgentAssignmentDialogProps> = ({
  open,
  onOpenChange,
  task,
  onClose,
  onAssign,
  availableSeats,
  availableSeatsError = false,
  saving = false
}) => {
  const [selectedSeats, setSelectedSeats] = React.useState<string[]>([]);
  const [seatSearchQuery, setSeatSearchQuery] = React.useState("");

  // Update selected seats when task changes
  React.useEffect(() => {
    if (task) {
      setSelectedSeats(task.assignees || []);
    }
  }, [task]);

  const toggleSeatSelection = (seatKey: string) => {
    setSelectedSeats(prev =>
      prev.includes(seatKey)
        ? prev.filter(key => key !== seatKey)
        : [...prev, seatKey]
    );
  };

  const handleAssign = () => {
    onAssign(selectedSeats);
  };

  const handleCancel = () => {
    // Reset to original task assignees
    setSelectedSeats(task?.assignees || []);
    onClose();
  };

  // Filter available seats based on search query
  const filteredAvailableSeats = React.useMemo(() => {
    if (!seatSearchQuery.trim()) {
      return availableSeats;
    }
    const query = seatSearchQuery.toLowerCase();
    return availableSeats.filter(seatKey =>
      seatKey.toLowerCase().includes(query)
    );
  }, [availableSeats, seatSearchQuery]);


  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-5xl w-[90vw]">
          <DialogHeader>
            <DialogTitle className="text-xl text-left">Assign Seats to Task</DialogTitle>
          </DialogHeader>

        <div className="space-y-4">
          {/* Task Information */}
          <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded">
            <h4 className="font-medium text-sm mb-1">Task: {task?.title}</h4>
            {task?.assignees && task.assignees.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Currently assigned: {task.assignees.join(', ')}
              </p>
            )}
          </div>

          <Separator />

          {/* Available Seats */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-sm">Seats ({filteredAvailableSeats.length})</h4>
              <div className="relative w-64">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search seats..."
                  value={seatSearchQuery}
                  onChange={(e) => setSeatSearchQuery(e.target.value)}
                  className="pl-8 pr-3 h-8 text-sm"
                />
              </div>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto border dark:border-gray-700 rounded p-2">
              {filteredAvailableSeats.length === 0 ? (
                <p
                  className={`text-sm text-center py-4 ${availableSeatsError ? "text-destructive" : "text-muted-foreground"}`}
                  role={availableSeatsError ? "alert" : undefined}
                >
                  {availableSeatsError
                    ? "Could not load your seats. Close this dialog and open it again to retry."
                    : seatSearchQuery
                      ? `No seats found matching "${seatSearchQuery}"`
                      : "You have no seats yet. Seats are created on the Seats page."}
                </p>
              ) : (
                filteredAvailableSeats.map((seatKey) => (
                <div key={seatKey} className="border dark:border-gray-700 rounded p-2 hover:bg-gray-50 dark:hover:bg-gray-800">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id={`lib-${seatKey}`}
                        checked={selectedSeats.includes(seatKey)}
                        onCheckedChange={() => toggleSeatSelection(seatKey)}
                      />
                      <label
                        htmlFor={`lib-${seatKey}`}
                        className="cursor-pointer flex-1"
                      >
                        <div>
                          <p className="font-medium text-sm">{seatKey}</p>
                          <p className="text-xs text-muted-foreground">Seat key</p>
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
              )))
              }
            </div>
          </div>

          {/* Selected Seats Summary */}
          {selectedSeats.length > 0 && (
            <>
              <Separator />
              <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                <h4 className="font-medium text-sm mb-2">Selected Seats ({selectedSeats.length}):</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedSeats.map((seat, index) => (
                    <span
                      key={index}
                      className="text-xs bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-2 py-1 rounded"
                    >
                      {seat}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={saving}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleAssign}
            disabled={saving}
          >
            {saving ? "Assigning..." : "Assign Seats"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
};

export default AgentAssignmentDialog;
