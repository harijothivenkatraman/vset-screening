import React from "react";
import { CardsBlock } from "./CardsBlock";
import { ComparisonBlock } from "./ComparisonBlock";
import { KvBlock } from "./KvBlock";
import { ListBlock } from "./ListBlock";
import { OlistBlock } from "./OlistBlock";
import { ParaBlock } from "./ParaBlock";
import { TableBlock } from "./TableBlock";
import { UnknownBlock } from "./UnknownBlock";
import { FounderProfileBlock } from "./FounderProfileBlock";

export interface BlockProps {
  block: [string, string, ...unknown[]];
}

/**
 * Registry mapping block type names to their respective React renderer components.
 * To support new block types, register them here without modifying existing components (Open/Closed Principle).
 */
const BLOCK_RENDERERS: Record<string, React.ComponentType<BlockProps>> = {
  para: ParaBlock,
  kv: KvBlock,
  olist: OlistBlock,
  list: ListBlock,
  table: TableBlock,
  cards: CardsBlock,
  comparison: ComparisonBlock,
  founder_profile: FounderProfileBlock,
};

/**
 * Returns the renderer component for a block type, falling back to UnknownBlock if unregistered.
 */
export function getBlockRenderer(type: string): React.ComponentType<BlockProps> {
  return BLOCK_RENDERERS[type] || UnknownBlock;
}

/**
 * Register a new block renderer at runtime if needed.
 */
export function registerBlockRenderer(
  type: string,
  component: React.ComponentType<BlockProps>
): void {
  BLOCK_RENDERERS[type] = component;
}
