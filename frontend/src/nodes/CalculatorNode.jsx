import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';

const OPERATIONS = [
  { value: 'sum', label: 'Sum (+)', unary: false },
  { value: 'subtract', label: 'Subtract (-)', unary: false },
  { value: 'multiply', label: 'Multiply (*)', unary: false },
  { value: 'divide', label: 'Divide (/)', unary: false },
  { value: 'abs', label: 'Abs', unary: true },
  { value: 'max', label: 'Max', unary: false },
  { value: 'min', label: 'Min', unary: false },
  { value: 'floor', label: 'Floor', unary: true },
  { value: 'ceil', label: 'Ceil', unary: true },
  { value: 'x2', label: 'x2', unary: true },
];

function isUnaryOperation(operation) {
  const option = OPERATIONS.find((item) => item.value === operation);
  return option ? option.unary : false;
}

export default function CalculatorNode({ data }) {
  const calculations = data.config?.calculations || [];
  const count = calculations.length;

  return (
    <BaseNode icon="🧮" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div>{count} calculation{count !== 1 ? 's' : ''}</div>
      </div>
    </BaseNode>
  );
}

export function CalculatorPropsForm({ config, onChange }) {
  const calculations = config.calculations || [];

  const updateCalculation = (idx, field, value) => {
    const next = calculations.map((item, i) => (i === idx ? { ...item, [field]: value } : item));
    onChange({ ...config, calculations: next });
  };

  const addCalculation = () => {
    onChange({
      ...config,
      calculations: [
        ...calculations,
        {
          output_key: '',
          operation: 'sum',
          left: '',
          right: '',
        },
      ],
    });
  };

  const removeCalculation = (idx) => {
    onChange({
      ...config,
      calculations: calculations.filter((_, i) => i !== idx),
    });
  };

  return (
    <div className="space-y-3">
      <Label>Calculations</Label>
      {calculations.map((item, idx) => {
        const operation = String(item.operation || 'sum');
        const unary = isUnaryOperation(operation);
        return (
          <div key={idx} className="rounded-md border border-border p-2 space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs text-muted-foreground">Calculation {idx + 1}</Label>
              <button
                type="button"
                onClick={() => removeCalculation(idx)}
                className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
                title="Remove"
              >
                ×
              </button>
            </div>

            <Input
              placeholder="output variable (example: total)"
              value={item.output_key || ''}
              onChange={e => updateCalculation(idx, 'output_key', e.target.value)}
            />

            <select
              value={operation}
              onChange={e => updateCalculation(idx, 'operation', e.target.value)}
              className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
            >
              {OPERATIONS.map((op) => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>

            <Input
              placeholder="Left operand: 10, ${price}, #{SECRET_VALUE}"
              value={item.left || ''}
              onChange={e => updateCalculation(idx, 'left', e.target.value)}
            />

            {!unary && (
              <Input
                placeholder="Right operand: 2, ${tax}, #{LIMIT}"
                value={item.right || ''}
                onChange={e => updateCalculation(idx, 'right', e.target.value)}
              />
            )}

            <p className="text-[11px] text-muted-foreground">
              Accepts numeric literals, <code>{'${VAR}'}</code>, or <code>{'#{SECRET}'}</code>.
            </p>
          </div>
        );
      })}

      <Button variant="outline" size="sm" className="w-full mt-1" onClick={addCalculation}>
        + Add calculation
      </Button>

      <div className="flex items-center gap-2 pt-2">
        <Checkbox
          id="include-input-fields-calculator"
          checked={config.include_other_input_fields || false}
          onCheckedChange={(checked) =>
            onChange({ ...config, include_other_input_fields: checked === true })
          }
        />
        <Label
          htmlFor="include-input-fields-calculator"
          className="text-sm text-muted-foreground cursor-pointer"
        >
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
