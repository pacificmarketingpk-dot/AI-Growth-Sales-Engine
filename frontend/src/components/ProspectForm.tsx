import { FormEvent, useState } from "react";
import { api } from "../services/api";
import type { Prospect, ProspectDetail } from "../types";
import { Button, Field, Modal, useToast } from "./ui";

const FIELDS: { key: keyof Prospect; label: string; type?: string; placeholder?: string; wide?: boolean; area?: boolean }[] = [
  { key: "name", label: "Name *", placeholder: "Jordan Patel" },
  { key: "job_title", label: "Job title", placeholder: "Head of Marketing" },
  { key: "company", label: "Company", placeholder: "Company name" },
  { key: "website", label: "Website", placeholder: "example.com" },
  { key: "industry", label: "Industry", placeholder: "SaaS" },
  { key: "country", label: "Country", placeholder: "USA" },
  { key: "company_size", label: "Company size", placeholder: "11-50" },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone", type: "tel" },
  { key: "linkedin_url", label: "LinkedIn URL", placeholder: "https://www.linkedin.com/in/…", wide: true },
  { key: "company_description", label: "What the company does", wide: true, area: true },
  { key: "notes", label: "Notes", wide: true, area: true },
];

export function ProspectFormModal({ open, onClose, onSaved, initial }: {
  open: boolean; onClose: () => void; onSaved: (p: ProspectDetail) => void; initial?: Partial<Prospect> & { id?: number };
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(FIELDS.map((f) => [f.key, (initial?.[f.key] as string) ?? ""])));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!values.name.trim()) { setError("Name is required."); return; }
    setSaving(true); setError(null);
    try {
      const p = initial?.id
        ? await api.put<ProspectDetail>(`/api/prospects/${initial.id}`, values)
        : await api.post<ProspectDetail>("/api/prospects", values);
      toast(initial?.id ? "Prospect updated" : "Prospect saved");
      onSaved(p);
    } catch (err) { setError((err as Error).message); } finally { setSaving(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title={initial?.id ? "Edit prospect" : "Add prospect"} wide
      footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" type="submit" form="prospect-form" loading={saving}>Save prospect</Button></>}>
      <form id="prospect-form" onSubmit={submit} className="grid grid-cols-1 gap-4 sm:grid-cols-2" noValidate>
        {FIELDS.map((f) => (
          <div key={f.key} className={f.wide ? "sm:col-span-2" : ""}>
            <Field label={f.label}>{(id) => f.area
              ? <textarea id={id} className="input min-h-[88px]" value={values[f.key]} onChange={(e) => setValues({ ...values, [f.key]: e.target.value })} />
              : <input id={id} className="input" type={f.type ?? "text"} placeholder={f.placeholder} value={values[f.key]}
                  onChange={(e) => setValues({ ...values, [f.key]: e.target.value })} autoComplete="off" />}
            </Field>
          </div>
        ))}
        {error && <p role="alert" className="text-sm text-danger sm:col-span-2">{error}</p>}
      </form>
    </Modal>
  );
}
