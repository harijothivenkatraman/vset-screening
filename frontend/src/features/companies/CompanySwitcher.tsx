import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Building2, Check, ChevronDown, Search } from "lucide-react";
import { useCompanies } from "@/features/companies/hooks";
import { Avatar } from "@/shared/ui";

interface CompanySwitcherProps {
  currentSlug: string;
}

export const CompanySwitcher: React.FC<CompanySwitcherProps> = ({ currentSlug }) => {
  const navigate = useNavigate();
  const { sectionKey } = useParams<{ sectionKey?: string }>();
  const { data: companies, isLoading } = useCompanies();

  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedCompany = companies?.find((c) => c.slug === currentSlug);

  const filteredCompanies = (companies || []).filter((c) =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.slug.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (c.stage && c.stage.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus input when opening
  useEffect(() => {
    if (isOpen) {
      setSearchTerm("");
      setHighlightedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const selectCompany = (slug: string) => {
    setIsOpen(false);
    if (slug !== currentSlug) {
      const targetPath = sectionKey ? `/companies/${slug}/${sectionKey}` : `/companies/${slug}/company`;
      navigate(targetPath);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < filteredCompanies.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredCompanies[highlightedIndex]) {
        selectCompany(filteredCompanies[highlightedIndex].slug);
      }
    }
  };

  return (
    <div ref={containerRef} className="relative inline-block text-left">
      {/* Trigger Button */}
      <button
        type="button"
        role="combobox"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-controls="company-listbox"
        aria-label="Select company"
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        className="flex items-center gap-2.5 px-3 py-1.5 bg-white hover:bg-slate-50 active:bg-slate-100 rounded-md border border-slate-300 transition-colors shadow-2xs focus-visible:outline-2 focus-visible:outline-[#1e2a3a] cursor-pointer min-h-[38px]"
      >
        <Avatar name={selectedCompany?.name || currentSlug} size="sm" />
        <div className="flex flex-col text-left leading-tight">
          <span className="font-bold text-slate-900 text-sm">
            {isLoading ? "Loading..." : selectedCompany?.name || currentSlug}
          </span>
          {selectedCompany?.stage && (
            <span className="text-[10px] text-slate-500 font-medium">
              {selectedCompany.stage}
            </span>
          )}
        </div>
        <ChevronDown
          aria-hidden="true"
          className={`w-3.5 h-3.5 text-slate-500 shrink-0 ml-1 transition-transform duration-150 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div
          id="company-listbox"
          role="listbox"
          className="absolute left-0 mt-1.5 w-64 bg-white rounded-lg border border-slate-200 shadow-lg z-50 overflow-hidden"
        >
          {/* Search Field */}
          <div className="p-2 border-b border-slate-100 bg-slate-50 flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Search companies..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setHighlightedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              className="w-full text-xs bg-transparent border-0 outline-none text-slate-900 placeholder:text-slate-400"
            />
          </div>

          {/* Options List */}
          <div className="max-h-60 overflow-y-auto p-1 space-y-0.5">
            {filteredCompanies.length > 0 ? (
              filteredCompanies.map((c, idx) => {
                const isSelected = c.slug === currentSlug;
                const isHighlighted = idx === highlightedIndex;

                return (
                  <div
                    key={c.slug}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => selectCompany(c.slug)}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    className={`flex items-center justify-between px-3 py-2 rounded-md text-xs cursor-pointer transition-colors ${
                      isHighlighted
                        ? "bg-slate-100 text-slate-900"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Avatar name={c.name} size="sm" />
                      <div className="truncate">
                        <div className="font-semibold text-slate-900 truncate">
                          {c.name}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {c.stage || c.audienceLabel}
                        </div>
                      </div>
                    </div>
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-[#0369a1] shrink-0" />
                    )}
                  </div>
                );
              })
            ) : (
              <div className="p-3 text-center text-xs text-slate-500 italic">
                No matching companies found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
