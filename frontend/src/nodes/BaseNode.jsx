import { Handle, Position } from 'reactflow';

/**
 * Shared node card wrapper.
 * Props:
 *  - icon: emoji string
 *  - instanceName: display name for this node instance
 *  - inputs: number (0 or 1)
 *  - outputs: number (0 or 1)
 *  - selected: boolean (passed by React Flow)
 *  - children: node body content
 */
export default function BaseNode({ icon, instanceName, inputs = 1, outputs = 1, children }) {
  return (
    <div style={{ minWidth: 200 }}>
      {inputs > 0 && (
        <Handle type="target" position={Position.Left} id="input_1" />
      )}
      <div className="node-title-box">
        <span>{icon}</span>
        <span>{instanceName}</span>
      </div>
      <div className="node-body">
        {children}
      </div>
      {outputs > 0 && (
        <Handle type="source" position={Position.Right} id="output_1" />
      )}
    </div>
  );
}
