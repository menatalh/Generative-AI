import {useEffect, useState} from 'react';
import {A2uiSurface, basicCatalog} from '@a2ui/react/v0_9';
import {MessageProcessor, type SurfaceModel} from '@a2ui/web_core/v0_9';

async function loadMessages() {
  const text = await fetch('/output.jsonl', {cache: 'no-store'}).then(r => r.text());
  return text.split('\n').filter(Boolean).map(line => JSON.parse(line));
}

export default function App() {
  const [surfaces, setSurfaces] = useState<SurfaceModel<any>[]>([]);
  const [lastAction, setLastAction] = useState('');

  async function render() {
    const processor = new MessageProcessor([basicCatalog], action => {
      setLastAction(JSON.stringify(action, null, 2));
    });
    processor.processMessages(await loadMessages());
    setSurfaces(Array.from(processor.model.surfacesMap.values()));
  }

  useEffect(() => {
    render();
  }, []);

  return (
    <main>
      <header>
        <h1>A2UI Viewer</h1>
        <button onClick={render}>Reload output.jsonl</button>
      </header>

      {surfaces.length === 0 && <p>No UI yet. Run the chain first.</p>}
      {surfaces.map(surface => (
        <A2uiSurface key={surface.id} surface={surface} />
      ))}

      {lastAction && (
        <section>
          <h2>Action sent back to the agent</h2>
          <pre>{lastAction}</pre>
        </section>
      )}
    </main>
  );
}
