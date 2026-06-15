import SchedulerNode,           { SchedulerPropsForm }           from './SchedulerNode';
import SetVariablesNode,         { SetVariablesPropsForm }         from './SetVariablesNode';
import GetCurrentDateNode,       { GetCurrentDatePropsForm }       from './GetCurrentDateNode';
import AddTimeToDateNode,        { AddTimeToDatePropsForm }        from './AddTimeToDateNode';
import SubtractTimeFromDateNode, { SubtractTimeFromDatePropsForm } from './SubtractTimeFromDateNode';
import MergeNode,                { MergePropsForm }                from './MergeNode';
import WaitNode,                 { WaitPropsForm }                 from './WaitNode';
import HttpRequestNode,          { HttpRequestPropsForm }          from './HttpRequestNode';
import IfNode,                   { IfPropsForm }                   from './IfNode';
import FilterNode,               { FilterPropsForm }               from './FilterNode';
import StopAndErrorNode,         { StopAndErrorPropsForm }         from './StopAndErrorNode';
import SplitNode,                { SplitPropsForm }                from './SplitNode';
import AggregateNode,            { AggregatePropsForm }            from './AggregateNode';
import FormatDateNode,           { FormatDatePropsForm }           from './FormatDateNode';

// React Flow nodeTypes map
export const nodeTypes = {
  scheduler:               SchedulerNode,
  set_variables:           SetVariablesNode,
  get_current_date_utc:    GetCurrentDateNode,
  add_time_to_date:        AddTimeToDateNode,
  subtract_time_from_date: SubtractTimeFromDateNode,
  merge:                   MergeNode,
  wait:                    WaitNode,
  http_request:            HttpRequestNode,
  if:                      IfNode,
  filter:                  FilterNode,
  stop_and_error:          StopAndErrorNode,
  split:                   SplitNode,
  aggregate:               AggregateNode,
  format_date:             FormatDateNode,
};

// Metadata: label, icon, i/o counts, default config, props form component
export const NODE_META = {
  scheduler: {
    label: 'Scheduler',
    icon:  '⏱',
    description: 'Time interval trigger',
    inputs: 0,
    outputs: 1,
    defaultConfig: () => ({ interval: 60, unit: 'seconds' }),
    PropsForm: SchedulerPropsForm,
  },
  set_variables: {
    label: 'Set Variables',
    icon:  '📦',
    description: 'Assign key=value pairs',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({ variables: [], include_other_input_fields: false }),
    PropsForm: SetVariablesPropsForm,
  },
  get_current_date_utc: {
    label: 'Get Current Date UTC',
    icon:  '📅',
    description: 'datetime.now(UTC)',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({ output_var: 'current_date_utc', include_other_input_fields: false }),
    PropsForm: GetCurrentDatePropsForm,
  },
  add_time_to_date: {
    label: 'Add Time to Date',
    icon:  '⏩',
    description: 'date + timedelta',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({ input_var: '', days: 0, hours: 0, minutes: 0, seconds: 0, output_var: 'new_date', include_other_input_fields: false }),
    PropsForm: AddTimeToDatePropsForm,
  },
  subtract_time_from_date: {
    label: 'Subtract Time from Date',
    icon:  '⏪',
    description: 'date - timedelta',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({ input_var: '', days: 0, hours: 0, minutes: 0, seconds: 0, output_var: 'new_date', include_other_input_fields: false }),
    PropsForm: SubtractTimeFromDatePropsForm,
  },
  merge: {
    label: 'Merge',
    icon:  '⬡',
    description: 'Append inbound items',
    inputs: 2,
    outputs: 1,
    defaultConfig: () => ({ strategy: 'append', branch_count: 2 }),
    PropsForm: MergePropsForm,
  },
  wait: {
    label: 'Wait',
    icon:  '⏳',
    description: 'Pause for N seconds',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({ seconds: 1 }),
    PropsForm: WaitPropsForm,
  },
  http_request: {
    label: 'HTTP Request',
    icon:  '🌐',
    description: 'GET/POST with headers and JSON body',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({
      method: 'GET',
      url: 'https://api.example.com',
      query_params: [],
      headers: [],
      body_raw_json: '{\n  "key": "${VALUE}"\n}',
      timeout_seconds: 30,
      include_other_input_fields: true,
    }),
    PropsForm: HttpRequestPropsForm,
  },
  if: {
    label: 'IF',
    icon:  '🔀',
    description: 'Branch by condition (true/false)',
    inputs: 1,
    outputs: 2,
    defaultConfig: () => ({
      input: '${value}',
      data_type: 'string',
      operator: 'equals',
      compare_value: '',
      conditions: [
        {
          join: 'and',
          input: '${value}',
          data_type: 'string',
          operator: 'equals',
          compare_value: '',
        },
      ],
    }),
    PropsForm: IfPropsForm,
  },
  filter: {
    label: 'Filter',
    icon:  '🧹',
    description: 'Keep only items matching conditions',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({
      input: '${value}',
      data_type: 'string',
      operator: 'equals',
      compare_value: '',
      conditions: [
        {
          join: 'and',
          input: '${value}',
          data_type: 'string',
          operator: 'equals',
          compare_value: '',
        },
      ],
    }),
    PropsForm: FilterPropsForm,
  },
  stop_and_error: {
    label: 'Stop and Error',
    icon:  '⛔',
    description: 'Stop current execution with custom message',
    inputs: 1,
    outputs: 0,
    defaultConfig: () => ({
      message: 'Execution stopped by business rule',
    }),
    PropsForm: StopAndErrorPropsForm,
  },
  split: {
    label: 'Split',
    icon:  '✂️',
    description: 'Split array into multiple items',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({
      input: '${items}',
      include_other_input_fields: true,
    }),
    PropsForm: SplitPropsForm,
  },
  aggregate: {
    label: 'Aggregate',
    icon:  '🧺',
    description: 'Collect all items into one list',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({
      output_var: 'items',
      include_other_input_fields: false,
    }),
    PropsForm: AggregatePropsForm,
  },
  format_date: {
    label: 'Format Date',
    icon:  '🗓️',
    description: 'Format a date to text/timestamp',
    inputs: 1,
    outputs: 1,
    defaultConfig: () => ({
      input: '${current_date_utc}',
      format: 'iso_8601',
      output_var: 'formatted_date',
      include_other_input_fields: false,
    }),
    PropsForm: FormatDatePropsForm,
  },
};
