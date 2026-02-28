import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Save, RefreshCw, ExternalLink, AlertCircle } from 'lucide-react';
import { apiClient, getComponentRenderUrl } from '../lib/api';
import type { ComponentUpdate } from '../types';

export function ComponentEditor() {
  const { namespace, name } = useParams<{ namespace: string; name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [sourceCode, setSourceCode] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [cssOverrides, setCssOverrides] = useState('');
  const [visibility, setVisibility] = useState('private');
  const [dirty, setDirty] = useState(false);

  const { data: component, isLoading } = useQuery({
    queryKey: ['component', namespace, name],
    queryFn: () => apiClient.getComponent(namespace!, name!),
    enabled: !!namespace && !!name,
    refetchInterval: (query) => {
      const status = query.state.data?.compile_status;
      if (status === 'pending' || status === 'compiling') return 2000;
      return false;
    },
  });

  useEffect(() => {
    if (component) {
      setSourceCode(component.source_code);
      setTitle(component.title || '');
      setDescription(component.description || '');
      setCssOverrides(component.css_overrides || '');
      setVisibility(component.visibility);
      setDirty(false);
    }
  }, [component]);

  const updateMutation = useMutation({
    mutationFn: (data: ComponentUpdate) =>
      apiClient.updateComponent(namespace!, name!, data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['components'] });
      queryClient.invalidateQueries({ queryKey: ['component', namespace, name] });
      setDirty(false);
      if (updated.namespace !== namespace || updated.name !== name) {
        navigate(`/components/${updated.namespace}/${updated.name}`, { replace: true });
      }
    },
  });

  const compileMutation = useMutation({
    mutationFn: () => apiClient.compileComponent(namespace!, name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['component', namespace, name] });
    },
  });

  const handleSave = useCallback(() => {
    const data: ComponentUpdate = {};
    if (sourceCode !== component?.source_code) data.source_code = sourceCode;
    if (title !== (component?.title || '')) data.title = title || undefined;
    if (description !== (component?.description || '')) data.description = description || undefined;
    if (cssOverrides !== (component?.css_overrides || '')) data.css_overrides = cssOverrides || undefined;
    if (visibility !== component?.visibility) data.visibility = visibility;

    if (Object.keys(data).length === 0) return;
    updateMutation.mutate(data);
  }, [sourceCode, title, description, cssOverrides, visibility, component, updateMutation]);

  // Ctrl+S save shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (dirty) handleSave();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [dirty, handleSave]);

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      success: 'bg-green-900/30 text-green-400 border-green-800',
      pending: 'bg-yellow-900/30 text-yellow-400 border-yellow-800',
      compiling: 'bg-blue-900/30 text-blue-400 border-blue-800',
      error: 'bg-red-900/30 text-red-400 border-red-800',
    };
    return colors[status] || 'bg-gray-900/30 text-gray-400 border-gray-800';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!component) {
    return (
      <div className="p-6 text-gray-400">Component not found</div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-[#0d0d0d]">
        <div className="flex items-center gap-3">
          <Link to="/components" className="text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-white">{component.title || component.name}</h1>
            <p className="text-xs text-gray-500">{namespace}/{name} &middot; v{component.version}</p>
          </div>
          <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getStatusBadge(component.compile_status)}`}>
            {component.compile_status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {component.compile_status === 'success' && (
            <a
              href={getComponentRenderUrl(component.render_token!, namespace!, name!)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Preview
            </a>
          )}
          <button
            onClick={() => compileMutation.mutate()}
            disabled={compileMutation.isPending}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${compileMutation.isPending ? 'animate-spin' : ''}`} />
            Compile
          </button>
          <button
            onClick={handleSave}
            disabled={!dirty || updateMutation.isPending}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            <Save className="w-4 h-4" />
            {updateMutation.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Compile errors */}
      {component.compile_status === 'error' && component.compile_errors?.length && (
        <div className="px-6 py-2 bg-red-900/10 border-b border-red-900/30">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <div>
              {component.compile_errors.map((err, i) => (
                <div key={i}>
                  {err.location ? `Line ${err.location.line}: ` : ''}{err.text}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Split pane: code editor left, preview right */}
      <div className="flex-1 flex overflow-hidden">
        {/* Code editor */}
        <div className="flex-1 flex flex-col border-r border-gray-800">
          {/* Metadata bar */}
          <div className="px-4 py-2 border-b border-gray-800 flex gap-4">
            <div className="flex-1">
              <input
                value={title}
                onChange={(e) => { setTitle(e.target.value); setDirty(true); }}
                placeholder="Title"
                className="w-full bg-transparent text-sm text-white focus:outline-none"
              />
            </div>
            <select
              value={visibility}
              onChange={(e) => { setVisibility(e.target.value); setDirty(true); }}
              className="bg-[#0d0d0d] border border-gray-800 rounded text-xs text-gray-400 px-2 py-1"
            >
              <option value="private">Private</option>
              <option value="shared">Shared</option>
              <option value="public">Public</option>
            </select>
          </div>

          {/* Source code textarea */}
          <textarea
            value={sourceCode}
            onChange={(e) => { setSourceCode(e.target.value); setDirty(true); }}
            className="flex-1 w-full bg-[#0a0a0a] text-gray-200 text-sm font-mono p-4 resize-none focus:outline-none"
            spellCheck={false}
          />

          {/* CSS overrides */}
          <div className="border-t border-gray-800">
            <div className="px-4 py-1 text-xs text-gray-500">CSS Overrides</div>
            <textarea
              value={cssOverrides}
              onChange={(e) => { setCssOverrides(e.target.value); setDirty(true); }}
              rows={3}
              className="w-full bg-[#0a0a0a] text-gray-300 text-xs font-mono px-4 py-2 resize-none focus:outline-none"
              placeholder="body { background: #1a1a2e; }"
              spellCheck={false}
            />
          </div>
        </div>

        {/* Preview iframe */}
        <div className="flex-1 flex flex-col bg-white">
          <div className="px-4 py-2 bg-[#111111] border-b border-gray-800 text-xs text-gray-500">
            Preview {component.compile_status !== 'success' && '(compile required)'}
          </div>
          {component.compile_status === 'success' ? (
            <iframe
              src={getComponentRenderUrl(component.render_token!, namespace!, name!)}
              className="flex-1 w-full border-0"
              title="Component Preview"
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
              Compile the component to see a preview
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
