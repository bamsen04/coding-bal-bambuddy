import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Palette, Plus, Trash2, Loader2, Check, X } from 'lucide-react';
import { api } from '../api/client';
import type { FilamentColorEntry } from '../api/client';
import { Card, CardHeader, CardContent } from '../components/Card';
import { Button } from '../components/Button';
import { ConfirmModal } from '../components/ConfirmModal';
import { useToast } from '../contexts/ToastContext';

const FILAMENT_TYPE_OPTIONS = ['PLA', 'PETG', 'ABS', 'TPU', 'ASA', 'PC', 'PA', 'PVA'];
const BRAND_OPTIONS = ['Generic', 'Bambu Lab'];

export function FilamentColorsPage() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [entries, setEntries] = useState<FilamentColorEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [deleteEntry, setDeleteEntry] = useState<FilamentColorEntry | null>(null);

  const [formColorName, setFormColorName] = useState('');
  const [formHexColor, setFormHexColor] = useState('#FFFFFF');
  const [formFilamentType, setFormFilamentType] = useState(FILAMENT_TYPE_OPTIONS[0]);
  const [formBrand, setFormBrand] = useState(BRAND_OPTIONS[0]);

  const loadEntries = useCallback(async () => {
    try {
      const data = await api.listFilamentColors();
      setEntries(data);
    } catch {
      showToast(t('filamentColors.loadFailed'), 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast, t]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const resetForm = () => {
    setFormColorName('');
    setFormHexColor('#FFFFFF');
    setFormFilamentType(FILAMENT_TYPE_OPTIONS[0]);
    setFormBrand(BRAND_OPTIONS[0]);
  };

  const handleAdd = async () => {
    if (!formColorName.trim() || !formHexColor) {
      showToast(t('filamentColors.fieldsRequired'), 'error');
      return;
    }
    setSaving(true);
    try {
      const entry = await api.createFilamentColor({
        color_name: formColorName.trim(),
        hex_color: formHexColor,
        filament_type: formFilamentType,
        brand: formBrand,
      });
      setEntries((prev) => [...prev, entry].sort((a, b) =>
        a.filament_type.localeCompare(b.filament_type) || a.color_name.localeCompare(b.color_name)
      ));
      setShowAddForm(false);
      resetForm();
      showToast(t('filamentColors.added'), 'success');
    } catch {
      showToast(t('filamentColors.addFailed'), 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteEntry) return;
    try {
      await api.deleteFilamentColor(deleteEntry.id);
      setEntries((prev) => prev.filter((e) => e.id !== deleteEntry.id));
      showToast(t('filamentColors.deleted'), 'success');
    } catch {
      showToast(t('filamentColors.deleteFailed'), 'error');
    } finally {
      setDeleteEntry(null);
    }
  };

  return (
    <div className="p-4 md:p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Palette className="w-7 h-7 text-bambu-green" />
          {t('filamentColors.title')}
        </h1>
        <p className="text-bambu-gray mt-1">{t('filamentColors.description')}</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <span className="text-sm text-bambu-gray">{t('filamentColors.count', { count: entries.length })}</span>
            <Button size="sm" onClick={() => setShowAddForm(true)}>
              <Plus className="w-4 h-4" />
              {t('common.add')}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {showAddForm && (
            <div className="p-4 bg-bambu-dark rounded-lg border border-bambu-dark-tertiary">
              <h3 className="text-sm font-medium text-white mb-3">{t('filamentColors.addNew')}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 items-end">
                <input
                  type="text"
                  className="px-3 py-2 bg-bambu-dark-secondary border border-bambu-dark-tertiary rounded-lg text-white placeholder-bambu-gray focus:border-bambu-green focus:outline-none"
                  placeholder={t('filamentColors.colorName')}
                  value={formColorName}
                  onChange={(e) => setFormColorName(e.target.value)}
                />
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    className="w-12 h-10 rounded cursor-pointer border border-bambu-dark-tertiary"
                    value={formHexColor}
                    onChange={(e) => setFormHexColor(e.target.value)}
                  />
                  <input
                    type="text"
                    className="flex-1 px-3 py-2 bg-bambu-dark-secondary border border-bambu-dark-tertiary rounded-lg text-white placeholder-bambu-gray focus:border-bambu-green focus:outline-none"
                    placeholder="#FFFFFF"
                    value={formHexColor}
                    onChange={(e) => setFormHexColor(e.target.value)}
                  />
                </div>
                <select
                  className="px-3 py-2 bg-bambu-dark-secondary border border-bambu-dark-tertiary rounded-lg text-white focus:border-bambu-green focus:outline-none"
                  value={formFilamentType}
                  onChange={(e) => setFormFilamentType(e.target.value)}
                >
                  {FILAMENT_TYPE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
                <select
                  className="px-3 py-2 bg-bambu-dark-secondary border border-bambu-dark-tertiary rounded-lg text-white focus:border-bambu-green focus:outline-none"
                  value={formBrand}
                  onChange={(e) => setFormBrand(e.target.value)}
                >
                  {BRAND_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleAdd}
                    disabled={saving}
                    className="flex-1 px-3 py-2 bg-bambu-green text-white rounded-lg hover:bg-bambu-green/80 flex items-center justify-center gap-2"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    {t('common.add')}
                  </button>
                  <button
                    onClick={() => { setShowAddForm(false); resetForm(); }}
                    className="p-2 rounded-lg text-bambu-gray hover:text-white hover:bg-bambu-dark-tertiary"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8 text-bambu-gray">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              {t('common.loading')}
            </div>
          ) : (
            <div className="overflow-auto border border-bambu-dark-tertiary rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-bambu-dark sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-bambu-gray font-medium w-12"></th>
                    <th className="px-3 py-2 text-left text-bambu-gray font-medium">{t('filamentColors.colorName')}</th>
                    <th className="px-3 py-2 text-left text-bambu-gray font-medium w-24">{t('filamentColors.hex')}</th>
                    <th className="px-3 py-2 text-left text-bambu-gray font-medium">{t('filamentColors.type')}</th>
                    <th className="px-3 py-2 text-left text-bambu-gray font-medium">{t('filamentColors.brand')}</th>
                    <th className="px-3 py-2 w-16"></th>
                  </tr>
                </thead>
                <tbody>
                  {entries.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-3 py-8 text-center text-bambu-gray">
                        {t('filamentColors.empty')}
                      </td>
                    </tr>
                  ) : (
                    entries.map((entry) => (
                      <tr key={entry.id} className="border-t border-bambu-dark-tertiary hover:bg-bambu-dark">
                        <td className="px-3 py-2">
                          <div
                            className="w-8 h-8 rounded border border-bambu-dark-tertiary"
                            style={{ backgroundColor: entry.hex_color }}
                            title={entry.hex_color}
                          />
                        </td>
                        <td className="px-3 py-2 text-white">{entry.color_name}</td>
                        <td className="px-3 py-2 font-mono text-xs text-bambu-gray">{entry.hex_color}</td>
                        <td className="px-3 py-2 text-bambu-gray">{entry.filament_type}</td>
                        <td className="px-3 py-2 text-bambu-gray">{entry.brand}</td>
                        <td className="px-3 py-2">
                          <div className="flex justify-end">
                            <button
                              onClick={() => setDeleteEntry(entry)}
                              className="p-1.5 rounded bg-red-500/10 hover:bg-red-500/20 text-red-500"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {deleteEntry && (
        <ConfirmModal
          title={t('filamentColors.deleteTitle')}
          message={t('filamentColors.deleteConfirm', { name: deleteEntry.color_name })}
          confirmText={t('common.delete')}
          variant="danger"
          onConfirm={handleDelete}
          onCancel={() => setDeleteEntry(null)}
        />
      )}
    </div>
  );
}
