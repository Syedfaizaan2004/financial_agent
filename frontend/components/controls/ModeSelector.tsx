import { useState } from "react";
import { ChevronDown } from "lucide-react";

export type ModeType = "quick" | "deep";

interface ModeSelectorProps {
    selectedMode: ModeType;
    onChange: (mode: ModeType) => void;
}

export default function ModeSelector({ selectedMode, onChange }: ModeSelectorProps) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="relative inline-block text-left z-20">
            <div>
                <button
                    type="button"
                    onClick={() => setIsOpen(!isOpen)}
                    className="inline-flex w-36 justify-between gap-1 rounded-md bg-zinc-900/80 px-4 py-2 text-sm font-semibold text-zinc-100 shadow-sm ring-1 ring-inset ring-zinc-700 hover:bg-zinc-800 transition-colors duration-200"
                    id="mode-selector-button"
                    aria-expanded={isOpen}
                    aria-haspopup="true"
                >
                    {selectedMode === "quick" ? "⚡ Quick Mode" : "🧠 Deep Mode"}
                    <ChevronDown className="-mr-1 h-5 w-5 text-zinc-400" aria-hidden="true" />
                </button>
            </div>

            {isOpen && (
                <div
                    className="absolute right-0 z-20 mt-2 w-48 origin-top-right rounded-md bg-zinc-900 shadow-xl ring-1 ring-white/10 ring-opacity-5 focus:outline-none overflow-hidden"
                    role="menu"
                    aria-orientation="vertical"
                    aria-labelledby="mode-selector-button"
                    tabIndex={-1}
                >
                    <div className="py-1" role="none">
                        <button
                            onClick={() => {
                                onChange("quick");
                                setIsOpen(false);
                            }}
                            className={`${selectedMode === "quick" ? "bg-zinc-800 text-white" : "text-zinc-300"
                                } group flex w-full items-center px-4 py-3 text-sm hover:bg-zinc-800 hover:text-white transition-colors duration-200`}
                            role="menuitem"
                            tabIndex={-1}
                        >
                            <div className="flex flex-col text-left">
                                <span className="font-medium text-emerald-400">⚡ Quick Mode</span>
                                <span className="text-xs text-zinc-500 mt-1">Summary, key risks, outlook</span>
                            </div>
                        </button>
                        <button
                            onClick={() => {
                                onChange("deep");
                                setIsOpen(false);
                            }}
                            className={`${selectedMode === "deep" ? "bg-zinc-800 text-white" : "text-zinc-300"
                                } group flex w-full items-center px-4 py-3 text-sm border-t border-zinc-800 hover:bg-zinc-800 hover:text-white transition-colors duration-200`}
                            role="menuitem"
                            tabIndex={-1}
                        >
                            <div className="flex flex-col text-left">
                                <span className="font-medium text-purple-400">🧠 Deep Mode</span>
                                <span className="text-xs text-zinc-500 mt-1">Full research, scenarios, memos</span>
                            </div>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
