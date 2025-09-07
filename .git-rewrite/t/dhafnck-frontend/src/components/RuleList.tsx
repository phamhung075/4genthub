import React, { useEffect, useState } from "react";
import { createRule, deleteRule, listRules, Rule, updateRule, validateRule } from "../api";
import { Alert } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Table } from "./ui/table";
import { RefreshButton } from "./ui/refresh-button";

const emptyRule: Partial<Rule> = { name: "", description: "", type: "custom", content: "" };

export default function RuleList() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRule, setSelectedRule] = useState<Rule | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [dialogMode, setDialogMode] = useState<"view" | "edit" | "create">("view");
  const [form, setForm] = useState<Partial<Rule>>(emptyRule);
  const [validateResult, setValidateResult] = useState<any>(null);
  const [validateLoading, setValidateLoading] = useState(false);

  const fetchRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listRules();
      setRules(data);
    } catch (e) {
      setError("Failed to load rules");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const openDialog = (mode: "view" | "edit" | "create", rule?: Rule) => {
    setDialogMode(mode);
    if (mode === "create") {
      setForm(emptyRule);
      setSelectedRule(null);
    } else if (rule) {
      setForm(rule);
      setSelectedRule(rule);
    }
    setShowDialog(true);
    setValidateResult(null);
  };

  const closeDialog = () => {
    setShowDialog(false);
    setSelectedRule(null);
    setForm(emptyRule);
    setValidateResult(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleCreate = async () => {
    try {
      const created = await createRule(form);
      if (created) {
        fetchRules();
        closeDialog();
      }
    } catch {
      setError("Failed to create rule");
    }
  };

  const handleUpdate = async () => {
    if (!selectedRule) return;
    try {
      const updated = await updateRule(selectedRule.id, form);
      if (updated) {
        fetchRules();
        closeDialog();
      }
    } catch {
      setError("Failed to update rule");
    }
  };

  const handleDelete = async (rule: Rule) => {
    if (!window.confirm(`Delete rule '${rule.name}'?`)) return;
    try {
      await deleteRule(rule.id);
      fetchRules();
    } catch {
      setError("Failed to delete rule");
    }
  };

  const handleValidate = async (rule: Rule) => {
    setValidateLoading(true);
    setValidateResult(null);
    try {
      const result = await validateRule(rule.id);
      setValidateResult(result);
    } catch {
      setValidateResult({ success: false, error: "Validation failed" });
    } finally {
      setValidateLoading(false);
    }
  };

  return (
    <Card className="p-6 dark:bg-gray-900 bg-white shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Rules</h2>
        <div className="flex gap-2">
          <RefreshButton 
            onClick={fetchRules} 
            loading={loading}
            size="sm"
          />
          <Button onClick={() => openDialog("create")}>New Rule</Button>
        </div>
      </div>
      {error && <Alert variant="destructive">{error}</Alert>}
      <Table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan={4}>Loading...</td></tr>
          ) : rules.length === 0 ? (
            <tr><td colSpan={4}>No rules found.</td></tr>
          ) : (
            rules.map(rule => (
              <tr key={rule.id} className="hover:bg-gray-100 dark:hover:bg-gray-800">
                <td className="font-medium cursor-pointer" onClick={() => openDialog("view", rule)}>{rule.name}</td>
                <td><Badge>{rule.type || "custom"}</Badge></td>
                <td>{rule.description}</td>
                <td className="space-x-2">
                  <Button size="sm" variant="outline" onClick={() => openDialog("view", rule)}>View</Button>
                  <Button size="sm" variant="secondary" onClick={() => openDialog("edit", rule)}>Edit</Button>
                  <Button size="sm" variant="outline" className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900" onClick={() => handleDelete(rule)}>Delete</Button>
                  <Button size="sm" variant="ghost" onClick={() => handleValidate(rule)} disabled={validateLoading}>Validate</Button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </Table>
      <Dialog open={showDialog} onOpenChange={closeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogMode === "create" ? "Create Rule" : dialogMode === "edit" ? "Edit Rule" : "Rule Details"}
            </DialogTitle>
          </DialogHeader>
          {dialogMode === "view" && selectedRule && (
            <div className="space-y-2">
              <div><strong>Name:</strong> {selectedRule.name}</div>
              <div><strong>Type:</strong> {selectedRule.type}</div>
              <div><strong>Description:</strong> {selectedRule.description}</div>
              <div><strong>Content:</strong>
                <pre className="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto max-h-48">{selectedRule.content}</pre>
              </div>
            </div>
          )}
          {(dialogMode === "edit" || dialogMode === "create") && (
            <form className="space-y-3" onSubmit={e => { e.preventDefault(); dialogMode === "create" ? handleCreate() : handleUpdate(); }}>
              <Input name="name" placeholder="Name" value={form.name || ""} onChange={handleInputChange} required className="w-full" />
              <Input name="type" placeholder="Type" value={form.type || ""} onChange={handleInputChange} className="w-full" />
              <Input name="description" placeholder="Description" value={form.description || ""} onChange={handleInputChange} className="w-full" />
              <textarea name="content" placeholder="Rule Content" value={form.content || ""} onChange={handleInputChange} className="w-full min-h-[100px] rounded border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-2" />
              <div className="flex justify-end space-x-2">
                <Button type="button" variant="outline" onClick={closeDialog}>Cancel</Button>
                <Button type="submit">{dialogMode === "create" ? "Create" : "Update"}</Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
      {validateResult && (
        <Alert variant={validateResult.success ? "default" : "destructive"} className="mt-4">
          {validateResult.success ? "Rule is valid." : validateResult.error || "Validation failed."}
        </Alert>
      )}
    </Card>
  );
} 