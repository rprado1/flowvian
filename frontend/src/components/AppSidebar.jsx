import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useWorkflow } from '@/context/WorkflowContext';
import { NODE_META } from '@/nodes';

const CATEGORY_ORDER = ['Core', 'Date and Time', 'Data', 'Logic', 'Flow Control', 'Network'];

const NODE_CATEGORIES = {
  scheduler: 'Core',
  set_variables: 'Data',
  get_current_date_utc: 'Date and Time',
  add_time_to_date: 'Date and Time',
  subtract_time_from_date: 'Date and Time',
  format_date: 'Date and Time',
  merge: 'Flow Control',
  wait: 'Flow Control',
  http_request: 'Network',
  if: 'Logic',
  switch: 'Logic',
  filter: 'Logic',
  stop_and_error: 'Flow Control',
  split: 'Data',
  aggregate: 'Data',
  sort: 'Data',
  calculator: 'Data',
};

function getCategory(type) {
  return NODE_CATEGORIES[type] || 'Core';
}

export default function AppSidebar() {
  const {
    currentWfId,
    addNode,
    recentNodeTypes,
    clearRecentNodeTypes,
  } = useWorkflow();
  const [query, setQuery] = useState('');
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [collapsedCategories, setCollapsedCategories] = useState(() => ({
    Core: false,
    'Date and Time': false,
    Data: false,
    Logic: false,
    'Flow Control': false,
    Network: false,
  }));

  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setShowNodeModal(true);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const nodeEntries = useMemo(() => {
    const q = query.trim().toLowerCase();
    const entries = Object.entries(NODE_META).map(([type, meta]) => ({
      type,
      meta,
      category: getCategory(type),
    }));

    if (!q) return entries;

    return entries.filter(({ type, meta, category }) => {
      const haystack = [meta.label, meta.description, type, category].join(' ').toLowerCase();
      return haystack.includes(q);
    });
  }, [query]);

  const groupedNodes = useMemo(() => {
    const groups = new Map();
    nodeEntries.forEach((entry) => {
      if (!groups.has(entry.category)) groups.set(entry.category, []);
      groups.get(entry.category).push(entry);
    });

    return CATEGORY_ORDER
      .filter(category => groups.has(category))
      .map(category => ({ category, entries: groups.get(category) }));
  }, [nodeEntries]);

  const recentEntries = useMemo(() => {
    const valid = (recentNodeTypes || []).filter(type => NODE_META[type]);
    return valid.map(type => ({ type, meta: NODE_META[type] }));
  }, [recentNodeTypes]);

  const placeNode = (type) => {
    const ok = addNode(type);
    if (ok && showNodeModal) setShowNodeModal(false);
  };

  const toggleCategory = (name) => {
    setCollapsedCategories(prev => ({ ...prev, [name]: !prev[name] }));
  };

  const renderNodeItem = ({ type, meta }, compact = false) => (
    <div
      key={type}
      className={`palette-node ${compact ? 'palette-node-compact' : ''}`}
      draggable
      onDragStart={e => e.dataTransfer.setData('node-type', type)}
      onDoubleClick={() => placeNode(type)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter') placeNode(type);
      }}
      title="Drag to canvas or double click to add"
    >
      <span className="palette-node-icon">{meta.icon}</span>
      <div className="min-w-0">
        <div className="font-semibold text-xs leading-tight truncate">{meta.label}</div>
        {!compact && (
          <div className="text-xs text-muted-foreground leading-tight truncate">{meta.description}</div>
        )}
      </div>
    </div>
  );

  return (
    <aside
      className="flex flex-col border-r border-border overflow-hidden"
      style={{ width: 'var(--sidebar-w)', flexShrink: 0, background: 'hsl(var(--card))' }}
    >
      <div className="p-3 flex flex-col gap-2 flex-1 overflow-hidden">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Nodes
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => setShowNodeModal(true)}
            disabled={!currentWfId}
            title="Open full node selector (Ctrl+K)"
          >
            Explore
          </Button>
        </div>

        <Input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search nodes..."
          className="h-8 text-xs"
        />

        {recentEntries.length > 0 && (
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-wide text-muted-foreground">Recent</span>
              <button
                className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                onClick={clearRecentNodeTypes}
                type="button"
              >
                clear
              </button>
            </div>
            <div className="grid grid-cols-2 gap-1">
              {recentEntries.slice(0, 4).map(entry => renderNodeItem(entry, true))}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {groupedNodes.map(group => (
            <div key={group.category} className="rounded-md border border-border/70 bg-muted/20">
              <button
                className="w-full text-left px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground transition-colors flex items-center justify-between"
                type="button"
                onClick={() => toggleCategory(group.category)}
              >
                <span>{group.category}</span>
                <span>{collapsedCategories[group.category] ? '+' : '-'}</span>
              </button>
              {!collapsedCategories[group.category] && (
                <div className="p-1 space-y-1">
                  {group.entries.map(entry => renderNodeItem(entry))}
                </div>
              )}
            </div>
          ))}
          {groupedNodes.length === 0 && (
            <p className="text-xs text-muted-foreground px-1 py-2">No nodes match your search</p>
          )}
        </div>
      </div>

      <Dialog open={showNodeModal} onOpenChange={setShowNodeModal}>
        <DialogContent className="max-w-4xl p-0 overflow-hidden">
          <DialogHeader className="px-6 pt-5 pb-2">
            <DialogTitle>Node Selector</DialogTitle>
            <DialogDescription>
              Search by name, drag from the list, or double click to place a node.
            </DialogDescription>
          </DialogHeader>

          <div className="px-6 pb-5">
            <Input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search by node name, type, or category"
              className="mb-3"
              autoFocus
            />

            <div className="max-h-[60vh] overflow-y-auto pr-1">
              {groupedNodes.map(group => (
                <div key={`modal-${group.category}`} className="mb-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1 px-1">
                    {group.category}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {group.entries.map(entry => renderNodeItem(entry))}
                  </div>
                </div>
              ))}
              {groupedNodes.length === 0 && (
                <p className="text-sm text-muted-foreground py-4">No results for current search.</p>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </aside>
  );
}
