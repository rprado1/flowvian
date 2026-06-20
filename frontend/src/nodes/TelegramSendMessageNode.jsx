import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';

export default function TelegramSendMessageNode({ data }) {
  const chatId = data.config?.chat_id || '${TELEGRAM_CHAT_ID}';
  const out = data.config?.output_var || 'telegram_result';

  return (
    <BaseNode icon="✈️" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div className="font-semibold truncate max-w-[180px]">Telegram</div>
        <div className="text-muted-foreground truncate max-w-[180px]">{chatId}</div>
        <div className="text-muted-foreground truncate max-w-[180px]">{out}</div>
      </div>
    </BaseNode>
  );
}

export function TelegramSendMessagePropsForm({ config, onChange }) {
  const includeFields = !!config.include_other_input_fields;

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label>Base URL</Label>
        <Input
          value={config.base_url || 'https://api.telegram.org'}
          placeholder="https://api.telegram.org"
          onChange={e => onChange({ ...config, base_url: e.target.value })}
        />
      </div>

      <div className="prop-group">
        <Label>Access Token</Label>
        <Input
          type="password"
          autoComplete="off"
          value={config.access_token || ''}
          placeholder="#{TELEGRAM_BOT_TOKEN}"
          onChange={e => onChange({ ...config, access_token: e.target.value })}
        />
      </div>

      <div className="prop-group">
        <Label>Chat ID</Label>
        <Input
          value={config.chat_id || '${TELEGRAM_CHAT_ID}'}
          placeholder="${TELEGRAM_CHAT_ID}"
          onChange={e => onChange({ ...config, chat_id: e.target.value })}
        />
        <p className="text-[11px] text-muted-foreground">
          Recommended: <code>${'{'}TELEGRAM_CHAT_ID{'}'}</code>
        </p>
      </div>

      <div className="prop-group">
        <Label>Message</Label>
        <Textarea
          value={config.message || ''}
          placeholder="Workflow finalizado para ${customer_name}"
          onChange={e => onChange({ ...config, message: e.target.value })}
          className="text-xs min-h-[100px]"
        />
        <p className="text-[11px] text-muted-foreground">
          Supports <code>${'{'}VAR{'}'}</code> and <code>#{'{'}SECRET{'}'}</code> placeholders.
        </p>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Checkbox
          id="telegram-disable-notification"
          checked={config.disable_notification === true}
          onCheckedChange={(checked) => onChange({ ...config, disable_notification: checked === true })}
        />
        <Label htmlFor="telegram-disable-notification" className="text-sm text-muted-foreground cursor-pointer">
          Disable Notification
        </Label>
      </div>

      <div className="prop-group">
        <Label>Output variable</Label>
        <Input
          value={config.output_var || 'telegram_result'}
          placeholder="telegram_result"
          onChange={e => onChange({ ...config, output_var: e.target.value })}
        />
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Checkbox
          id="telegram-include-fields"
          checked={includeFields}
          onCheckedChange={(checked) => onChange({ ...config, include_other_input_fields: checked === true })}
        />
        <Label htmlFor="telegram-include-fields" className="text-sm text-muted-foreground cursor-pointer">
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
