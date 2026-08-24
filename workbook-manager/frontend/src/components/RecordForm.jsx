import React, { useEffect, useMemo, useRef, useState } from "react";
import { Check } from "lucide-react";
import { api } from "../api.js";
import { isDraftDirty, validateDraft, validateField } from "../editorValidation.js";
import EditorShell from "./EditorShell.jsx";

function blankOption(control, prompt = "Choose a value") {
  if (control.blank === "forbidden" || control.blank === "never_blank_key") {
    return <option value="">{prompt}</option>;
  }
  return <option value="">Not specified / inherit</option>;
}

function BooleanControl({ column, value, onChange, onBlur, disabled, id }) {
  const control = column.control;
  return (
    <select id={id} className="select" value={value ?? ""} onChange={onChange} onBlur={onBlur} disabled={disabled}>
      {blankOption(control)}
      {control.values.map((choice) => (
        <option key={choice} value={choice}>
          {choice === "True" ? "Yes" : choice === "False" ? "No" : choice}
        </option>
      ))}
    </select>
  );
}

function FiniteControl({ column, value, onChange, onBlur, disabled, id }) {
  const control = column.control;
  return (
    <select id={id} className="select" value={value ?? ""} onChange={onChange} onBlur={onBlur} disabled={disabled}>
      {blankOption(control)}
      {control.values.filter((choice) => choice !== "").map((choice) => (
        <option key={choice} value={choice}>{choice}</option>
      ))}
    </select>
  );
}

function ReferenceControl({
  column, value, onChange, onBlur, disabled, id, referenceState, onReferenceQuery,
}) {
  const [query, setQuery] = useState("");
  const control = column.control;
  const state = referenceState || { options: [], loading: true };
  return (
    <div className="reference-control">
      <input
        className="text"
        type="search"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          onReferenceQuery(event.target.value);
        }}
        placeholder={`Search ${control.label} choices`}
        aria-label={`Search ${control.label} choices`}
        disabled={disabled}
      />
      <select id={id} className="select" value={value ?? ""} onChange={onChange} onBlur={onBlur} disabled={disabled || state.loading}>
        {blankOption(control, state.loading ? "Loading choices…" : "Choose a reference")}
        {(state.options || []).map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}{option.secondary ? ` — ${option.secondary}` : ""}{option.active === false ? " (inactive)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

function NumberControl({ column, value, onChange, onBlur, disabled, id }) {
  const control = column.control;
  return (
    <input
      id={id}
      className="text"
      type="number"
      inputMode="numeric"
      value={value ?? ""}
      min={control.min}
      max={control.max}
      step={control.step || 1}
      onChange={onChange}
      onBlur={onBlur}
      disabled={disabled}
    />
  );
}

function UrlControl({ value, onChange, onBlur, disabled, id }) {
  return <input id={id} value={value ?? ""} onChange={onChange} onBlur={onBlur} disabled={disabled} className="text" type="url" inputMode="url" />;
}

function TextControl({ value, onChange, onBlur, disabled, id }) {
  return <input id={id} value={value ?? ""} onChange={onChange} onBlur={onBlur} disabled={disabled} className="text" type="text" />;
}

function TextAreaControl({ column, value, onChange, onBlur, disabled, id }) {
  return <textarea id={id} value={value ?? ""} onChange={onChange} onBlur={onBlur} disabled={disabled} className="text" rows={column.control.multiline || 4} />;
}

function ReadOnlyControl({ value, id }) {
  return <output id={id} className="editor-readonly">{value === "" || value == null ? "Not set" : String(value)}</output>;
}

export const CONTROL_RENDERERS = {
  boolean: BooleanControl,
  finite: FiniteControl,
  reference: ReferenceControl,
  integer: NumberControl,
  money: NumberControl,
  url: UrlControl,
  structured_text: TextAreaControl,
  short_text: TextControl,
  long_text: TextAreaControl,
  immutable: ReadOnlyControl,
  generated: ReadOnlyControl,
  read_only: ReadOnlyControl,
};

function initialDraft(schema, initial) {
  return Object.fromEntries(
    schema.columns.map((column) => [column.name, initial?.[column.name] ?? ""]),
  );
}

function initialReferenceStates(schema) {
  return Object.fromEntries(
    schema.columns
      .filter((column) => column.control.kind === "reference")
      .map((column) => [column.name, {
        options: [], loading: true, loaded: false, error: "",
      }]),
  );
}

function mergeOptions(...groups) {
  const merged = new Map();
  for (const option of groups.flat()) merged.set(String(option.value), option);
  return [...merged.values()].sort((left, right) =>
    String(left.label || left.value).localeCompare(String(right.label || right.value))
  );
}

export default function RecordForm({
  schema, mode, initial, modelKey, onSaved, onCancel, saveFn,
}) {
  const [draft, setDraft] = useState(() => initialDraft(schema, initial));
  const [errors, setErrors] = useState({});
  const [generalErrors, setGeneralErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [referenceStates, setReferenceStates] = useState(() => initialReferenceStates(schema));
  const busyRef = useRef(false);
  const formRef = useRef(null);
  const referenceTokens = useRef({});

  const referenceColumns = useMemo(
    () => schema.columns.filter((column) => column.control.kind === "reference"),
    [schema],
  );
  const referenceSignature = useMemo(
    () => JSON.stringify(referenceColumns.map((column) => [
      column.name,
      column.reference?.discriminator
        ? draft[column.reference.discriminator] ?? ""
        : "",
    ])),
    [referenceColumns, draft],
  );

  const loadReference = async (column, query = "", reset = false) => {
    const token = (referenceTokens.current[column.name] || 0) + 1;
    referenceTokens.current[column.name] = token;
    setReferenceStates((states) => ({
      ...states,
      [column.name]: {
        options: reset ? [] : states[column.name]?.options || [],
        loading: true,
        loaded: false,
        error: "",
      },
    }));
    const discriminator = column.reference?.discriminator
      ? draft[column.reference.discriminator] ?? ""
      : "";
    try {
      const response = await api.referenceOptions(schema.table, column.name, {
        model: modelKey,
        query,
        discriminator,
        limit: 100,
      });
      let options = response.options || [];
      const current = String(draft[column.name] ?? "");
      if (current && !options.some((option) => String(option.value) === current)) {
        const currentResponse = await api.referenceOptions(schema.table, column.name, {
          model: modelKey,
          query: current,
          discriminator,
          limit: 25,
        });
        options = mergeOptions(options, currentResponse.options || []);
      }
      if (referenceTokens.current[column.name] !== token) return;
      setReferenceStates((states) => ({
        ...states,
        [column.name]: {
          options: mergeOptions(reset ? [] : states[column.name]?.options || [], options),
          loading: false,
          loaded: true,
          error: "",
        },
      }));
    } catch (error) {
      if (referenceTokens.current[column.name] !== token) return;
      setReferenceStates((states) => ({
        ...states,
        [column.name]: {
          options: [], loading: false, loaded: false, error: error.message,
        },
      }));
    }
  };

  useEffect(() => {
    referenceColumns.forEach((column) => loadReference(column, "", true));
  }, [schema, modelKey, referenceSignature]); // eslint-disable-line react-hooks/exhaustive-deps

  const setValue = (column, value) => {
    setDraft((current) => ({ ...current, [column.name]: value }));
    setErrors((current) => ({
      ...current,
      [column.name]: validateField(column, value, referenceStates[column.name]),
    }));
  };

  const validateOne = (column) => {
    setErrors((current) => ({
      ...current,
      [column.name]: validateField(
        column,
        draft[column.name],
        referenceStates[column.name],
      ),
    }));
  };

  const focusFirstInvalid = () => {
    window.requestAnimationFrame(() => {
      const firstInvalid = formRef.current?.querySelector(
        '[data-field-error="true"] input, [data-field-error="true"] select, [data-field-error="true"] textarea',
      );
      if (firstInvalid) firstInvalid.focus();
    });
  };

  const submit = async () => {
    if (busyRef.current) return;
    const localErrors = validateDraft(schema, draft, referenceStates);
    setErrors(localErrors);
    setGeneralErrors([]);
    if (Object.keys(localErrors).length) {
      focusFirstInvalid();
      return;
    }
    busyRef.current = true;
    setBusy(true);
    try {
      const key = Object.fromEntries(schema.key.map((name) => [
        name,
        mode === "edit" ? String(initial?.[name] ?? "") : String(draft[name] ?? ""),
      ]));
      const operation = await saveFn({
        table: schema.table,
        model_id: schema.model_context?.required
          ? (schema.model_context.value || modelKey)
          : "",
        op: mode === "edit" ? "update" : "add",
        key,
        record: draft,
      });
      onSaved(operation);
    } catch (error) {
      const backendErrors = error.detail?.errors || [{ message: error.message, field: "" }];
      const fieldErrors = {};
      const unscoped = [];
      for (const item of backendErrors) {
        if (item.field && schema.columns.some((column) => column.name === item.field)) {
          fieldErrors[item.field] = item.message;
        } else {
          unscoped.push(item.message);
        }
      }
      setErrors(fieldErrors);
      setGeneralErrors(unscoped);
      focusFirstInvalid();
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const dirty = isDraftDirty(schema, initial || {}, draft);
  const groupedColumns = useMemo(() => {
    const groups = new Map();
    for (const column of schema.columns) {
      const group = column.control.group || "Other";
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(column);
    }
    return [...groups.entries()].map(([group, columns]) => [
      group,
      columns.sort((left, right) => left.control.order - right.control.order),
    ]);
  }, [schema]);

  return (
    <EditorShell
      title={`${mode === "edit" ? "Edit" : "Add"} ${schema.label}`}
      subtitle="Changes are saved to the durable draft only. The workbook is not changed here."
      target={`${schema.label}${schema.sheet_for_model ? ` · ${schema.sheet_for_model}` : ""}`}
      dirty={dirty}
      busy={busy}
      onRequestClose={onCancel}
      footer={(requestClose) => (
        <>
          <button type="button" className="btn primary" onClick={submit} disabled={busy}>
            <Check size={15} /> {busy ? "Saving to draft…" : "Save change to draft"}
          </button>
          <button type="button" className="btn" onClick={requestClose} disabled={busy}>Cancel</button>
          <span className="muted">Draft only · no workbook write or rebuild</span>
        </>
      )}
    >
      <form ref={formRef} onSubmit={(event) => { event.preventDefault(); submit(); }} noValidate>
        {groupedColumns.map(([group, columns]) => (
          <fieldset className="editor-field-group" key={group}>
            <legend>{group}</legend>
            <div className="form-grid">
              {columns.map((column) => {
                const control = column.control;
                const Renderer = CONTROL_RENDERERS[control.kind];
                if (!Renderer) throw new Error(`Unsupported control kind: ${control.kind}`);
                const locked = mode === "edit" && control.immutable_on_edit;
                const readOnly = ["immutable", "generated", "read_only"].includes(control.kind);
                const error = errors[column.name] || "";
                const inputId = `editor-${schema.table}-${column.name}`;
                return (
                  <div
                    className="field"
                    key={column.name}
                    data-field-error={error ? "true" : "false"}
                  >
                    <label htmlFor={inputId}>
                      {control.label}
                      {control.blank === "forbidden" && <span className="required"> Required</span>}
                    </label>
                    <Renderer
                      id={inputId}
                      column={column}
                      value={draft[column.name]}
                      onChange={(event) => setValue(column, event.target.value)}
                      onBlur={() => validateOne(column)}
                      disabled={busy || locked || readOnly}
                      referenceState={referenceStates[column.name]}
                      onReferenceQuery={(query) => loadReference(column, query)}
                    />
                    {locked && <div className="ref-hint">Locked while editing this record.</div>}
                    {control.help && <div className="field-help">{control.help}</div>}
                    {error && <div className="field-error" role="alert">{error}</div>}
                  </div>
                );
              })}
            </div>
          </fieldset>
        ))}
        {generalErrors.map((message) => (
          <div className="notice err" role="alert" key={message}>{message}</div>
        ))}
      </form>
    </EditorShell>
  );
}