'use client'

import { useMemo, useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { NoteResponse, NotebookResponse, SourceListResponse } from '@/lib/types/api'
import { GraphCanvas, darkTheme, GraphEdge, GraphNode } from 'reagraph'
import { useTheme } from 'next-themes'

type SourceMode = 'off' | 'insights' | 'full'

interface NotebookSelection {
  sources: Record<string, SourceMode>
  notes: Record<string, SourceMode>
}

interface PodcastContextGraphProps {
  notebooks: NotebookResponse[]
  selections: Record<string, NotebookSelection>
  sourcesByNotebook: Record<string, SourceListResponse[]>
  notesByNotebook: Record<string, NoteResponse[]>
}

export function PodcastContextGraph({
  notebooks,
  selections,
  sourcesByNotebook,
  notesByNotebook,
}: PodcastContextGraphProps) {
  const { t } = useTranslation()
  const [activeIds, setActiveIds] = useState<string[]>([])
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme !== 'light'

  const neonTheme = useMemo(() => ({
    ...darkTheme,
    canvas: {
      ...darkTheme.canvas,
      background: isDark ? '#020617' : '#ffffff',
    },
    node: {
      ...darkTheme.node,
      color: isDark ? '#7dd3fc' : '#2563eb',
      activeFill: isDark ? '#86efac' : '#0ea5a4',
      label: {
        ...(darkTheme.node?.label ?? {}),
        color: isDark ? '#e0f2fe' : '#0f172a',
        stroke: isDark ? '#020617' : '#ffffff',
        activeColor: isDark ? '#ffffff' : '#020617',
      },
    },
    edge: {
      ...darkTheme.edge,
      fill: isDark ? '#c4b5fd99' : '#7c3aed55',
      activeFill: isDark ? '#ddd6fe' : '#7c3aed',
      label: {
        ...(darkTheme.edge?.label ?? {}),
        color: isDark ? '#dbeafe' : '#1f2937',
        stroke: isDark ? '#020617' : '#ffffff',
        activeColor: isDark ? '#ffffff' : '#111827',
      },
    },
  }), [isDark])

  const { nodes, edges, selectedCount } = useMemo(() => {
    const graphNodes: GraphNode[] = []
    const graphEdges: GraphEdge[] = []
    let count = 0

    for (const notebook of notebooks) {
      const selection = selections[notebook.id]
      if (!selection) {
        continue
      }

      const selectedSources = (sourcesByNotebook[notebook.id] ?? []).filter((source) => {
        const mode = selection.sources[source.id] ?? 'off'
        return mode !== 'off'
      })
      const selectedNotes = (notesByNotebook[notebook.id] ?? []).filter((note) => {
        const mode = selection.notes[note.id] ?? 'off'
        return mode !== 'off'
      })

      if (selectedSources.length === 0 && selectedNotes.length === 0) {
        continue
      }

      graphNodes.push({
        id: `notebook:${notebook.id}`,
        label: notebook.name,
        fill: '#c2a6ff',
        size: 10,
        data: { type: 'notebook' },
      })

      for (const source of selectedSources) {
        const mode = selection.sources[source.id]
        const sourceNodeId = `source:${source.id}`
        graphNodes.push({
          id: sourceNodeId,
          label: source.title || t.podcasts.untitledSource,
          fill: mode === 'insights' ? '#7af9b2' : '#6fc9ff',
          size: mode === 'insights' ? 7 : 8,
          data: { type: 'source', mode },
        })
        graphEdges.push({
          id: `edge:notebook-source:${notebook.id}:${source.id}`,
          source: sourceNodeId,
          target: `notebook:${notebook.id}`,
          size: mode === 'insights' ? 2 : 3,
        })
      }

      for (const note of selectedNotes) {
        const noteNodeId = `note:${note.id}`
        graphNodes.push({
          id: noteNodeId,
          label: note.title || t.podcasts.untitledNote,
          fill: '#ff9f43',
          size: 7,
          data: { type: 'note' },
        })
        graphEdges.push({
          id: `edge:notebook-note:${notebook.id}:${note.id}`,
          source: noteNodeId,
          target: `notebook:${notebook.id}`,
          size: 2,
        })
      }

      count += selectedSources.length + selectedNotes.length
    }

    return { nodes: graphNodes, edges: graphEdges, selectedCount: count }
  }, [notebooks, notesByNotebook, selections, sourcesByNotebook, t])

  if (selectedCount === 0) {
    return (
      <div className="rounded-lg border border-dashed bg-muted/20 p-4 text-xs text-muted-foreground">
        {t.podcasts.noContentSelected}
      </div>
    )
  }

  return (
    <div className={`relative z-0 rounded-lg p-3 ${isDark
      ? 'border border-cyan-300/45 bg-gradient-to-br from-[#020617] via-[#0b1228] to-[#1a1038] shadow-[0_0_36px_rgba(34,211,238,0.35),0_0_72px_rgba(168,85,247,0.22)]'
      : 'border border-slate-200 bg-gradient-to-br from-[#ffffff] via-[#f8fbff] to-[#f5f7ff] shadow-[0_8px_26px_rgba(15,23,42,0.08)]'
      }`}
    >
      <div
        className={`relative z-0 h-[240px] overflow-hidden rounded-md ${isDark
          ? 'border border-cyan-300/35'
          : 'border border-slate-200'
          }`}
      >
        <GraphCanvas
          nodes={nodes}
          edges={edges}
          theme={neonTheme}
          layoutType="forceDirected2d"
          cameraMode="pan"
          labelType="all"
          defaultNodeSize={8}
          draggable
          onNodeClick={(node) => setActiveIds([node.id])}
          selections={activeIds}
          actives={activeIds}
        />
      </div>
    </div>
  )
}
