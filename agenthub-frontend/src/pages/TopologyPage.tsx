/**
 * Topology Page - the workspace as rooms, seats and links.
 *
 * F6: rooms are the groups ("pods"), seats are the nodes and seat links are the
 * edges, drawn by kind. Live through the same realtime socket the seat pages
 * use (`useRealtimeSync` invalidates the topology query on seat events), not the
 * session stream - sessions are the runtime tail (C3); this is seat data.
 *
 * @module pages/TopologyPage
 * @version 1.0.0
 */

import React from 'react';
import { RefreshCw } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { TopologyGraph, TopologyLegend } from '../components/topology/TopologyGraph';
import { TopologySeatsTable } from '../components/topology/TopologySeatsTable';
import { useTopology } from '../hooks/useTopology';
import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../hooks/useWebSocketV2';
import { useRealtimeSync } from '../hooks/useRealtimeSync';
import { cn } from '../lib/utils';

export const TopologyPage: React.FC = () => {
  const { user, tokens } = useAuth();
  const webSocketClient = useWebSocket(user?.id || '', tokens?.access_token || '');
  useRealtimeSync(webSocketClient.client, true);

  const { rooms, isLoading, error, refetch } = useTopology();

  const seatCount = rooms.reduce((total, entry) => total + entry.seats.length, 0);
  const linkCount = rooms.reduce((total, entry) => total + entry.links.length, 0);

  return (
    <div className="mx-auto w-full max-w-6xl p-4 md:p-6">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-base-primary">Topology</h1>
          <p className="text-sm text-base-secondary">
            {rooms.length} {rooms.length === 1 ? 'room' : 'rooms'} · {seatCount}{' '}
            {seatCount === 1 ? 'seat' : 'seats'} · {linkCount}{' '}
            {linkCount === 1 ? 'link' : 'links'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={cn('mr-2 h-4 w-4', isLoading && 'animate-spin')} />
          Refresh
        </Button>
      </header>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>
            Could not load the topology: {error instanceof Error ? error.message : 'unknown error'}
          </AlertDescription>
        </Alert>
      )}

      {isLoading && rooms.length === 0 ? (
        <p className="py-10 text-center text-sm text-base-secondary">Loading topology…</p>
      ) : rooms.length === 0 ? (
        <p className="py-10 text-center text-sm text-base-secondary">
          No rooms yet. Create a room and add seats to see the topology.
        </p>
      ) : (
        <Tabs defaultValue="graph">
          <TabsList>
            <TabsTrigger value="graph">Graph</TabsTrigger>
            <TabsTrigger value="seats">Seats</TabsTrigger>
          </TabsList>

          <TabsContent value="graph" className="mt-4">
            <div className="mb-4">
              <TopologyLegend />
            </div>
            <TopologyGraph rooms={rooms} />
          </TabsContent>

          <TabsContent value="seats" className="mt-4">
            <TopologySeatsTable rooms={rooms} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
};
