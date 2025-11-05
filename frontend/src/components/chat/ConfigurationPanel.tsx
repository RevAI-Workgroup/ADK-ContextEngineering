'use client'

/**
 * Configuration Panel Component
 * 
 * Provides UI for configuring context engineering techniques
 * with Simple and Advanced modes
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Switch } from '../ui/switch'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion'
import { Input } from '../ui/input'
import { Slider } from '../ui/slider'
import { Settings, RotateCcw, Check, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '../ui/alert'
import {
  ContextEngineeringConfig,
  ConfigPreset,
  TECHNIQUE_NAMES,
  TECHNIQUE_DESCRIPTIONS,
  createDefaultConfig,
} from '../../types/config.types'
import { configService } from '../../services/configService'

interface ConfigurationPanelProps {
  config: ContextEngineeringConfig
  onConfigChange: (config: ContextEngineeringConfig) => void
  className?: string
}

export function ConfigurationPanel({ config, onConfigChange, className }: ConfigurationPanelProps) {
  const [activeTab, setActiveTab] = useState<'simple' | 'advanced'>('simple')
  const [presets, setPresets] = useState<Record<string, ContextEngineeringConfig>>({})
  const [selectedPreset, setSelectedPreset] = useState<ConfigPreset>('baseline')
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [validationSuccess, setValidationSuccess] = useState(false)

  // Load presets on mount
  useEffect(() => {
    loadPresets()
  }, [])

  const loadPresets = async () => {
    try {
      const response = await configService.getPresets()
      setPresets(response.presets)
    } catch (error) {
      console.error('Failed to load presets:', error)
    }
  }

  const handleTechniqueToggle = (technique: keyof ContextEngineeringConfig, enabled: boolean) => {
    const newConfig = { ...config }
    const techniqueConfig = newConfig[technique]
    if (typeof techniqueConfig === 'object' && techniqueConfig !== null && 'enabled' in techniqueConfig) {
      techniqueConfig.enabled = enabled
      onConfigChange(newConfig)
    }
  }

  const handlePresetChange = (preset: ConfigPreset) => {
    setSelectedPreset(preset)
    if (presets[preset]) {
      onConfigChange(presets[preset])
      setValidationErrors([])
      setValidationSuccess(false)
    }
  }

  const handleResetToDefault = () => {
    const defaultConfig = createDefaultConfig()
    onConfigChange(defaultConfig)
    setSelectedPreset('baseline')
    setValidationErrors([])
    setValidationSuccess(false)
  }

  const handleValidate = async () => {
    try {
      const result = await configService.validateConfig(config)
      setValidationErrors(result.errors || [])
      setValidationSuccess(result.valid)
      
      // Auto-dismiss success after 3 seconds
      if (result.valid) {
        setTimeout(() => setValidationSuccess(false), 3000)
      }
    } catch (error) {
      console.error('Validation error:', error)
      setValidationErrors(['Failed to validate configuration'])
      setValidationSuccess(false)
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            <CardTitle>Context Engineering Configuration</CardTitle>
          </div>
          <div className="flex items-center gap-1.5">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleValidate}
              className="h-7 px-2 text-xs"
            >
              <Check className="h-3 w-3 mr-1" />
              Save
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleResetToDefault}
              className="h-7 px-2 text-xs"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Reset
            </Button>
          </div>
        </div>
        <CardDescription>
          Configure which context engineering techniques to apply
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Validation Messages */}
        {validationSuccess && (
          <Alert>
            <Check className="h-4 w-4" />
            <AlertDescription>Configuration is valid!</AlertDescription>
          </Alert>
        )}
        
        {validationErrors.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <div className="font-semibold mb-1">Configuration errors:</div>
              <ul className="list-disc list-inside text-sm">
                {validationErrors.map((error, idx) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'simple' | 'advanced')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="simple">Simple</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          {/* Simple Tab */}
          <TabsContent value="simple" className="space-y-4">
            {/* Preset Selector */}
            <div className="space-y-2">
              <Label>Configuration Preset</Label>
              <div className="flex gap-2">
                <Select value={selectedPreset} onValueChange={handlePresetChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="baseline">Baseline (No techniques)</SelectItem>
                    <SelectItem value="basic_rag">Basic RAG</SelectItem>
                    <SelectItem value="advanced_rag">Advanced RAG</SelectItem>
                    <SelectItem value="full_stack">Full Stack</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Technique Toggles */}
            <div className="space-y-4">
              <Label className="text-base font-semibold">Enabled Techniques</Label>

              <TechniqueSwitch
                label={TECHNIQUE_NAMES.naive_rag}
                description={TECHNIQUE_DESCRIPTIONS.naive_rag}
                checked={config.naive_rag.enabled}
                onCheckedChange={(checked) => handleTechniqueToggle('naive_rag', checked)}
              />

              <TechniqueSwitch
                label={TECHNIQUE_NAMES.rag_tool}
                description={TECHNIQUE_DESCRIPTIONS.rag_tool}
                checked={config.rag_tool.enabled}
                onCheckedChange={(checked) => handleTechniqueToggle('rag_tool', checked)}
              />

              <TechniqueSwitch
                label={TECHNIQUE_NAMES.compression}
                description={TECHNIQUE_DESCRIPTIONS.compression}
                checked={config.compression.enabled}
                onCheckedChange={(checked) => handleTechniqueToggle('compression', checked)}
              />

              <TechniqueSwitch
                label={TECHNIQUE_NAMES.reranking}
                description={TECHNIQUE_DESCRIPTIONS.reranking}
                checked={config.reranking.enabled}
                onCheckedChange={(checked) => handleTechniqueToggle('reranking', checked)}
                disabled={!config.naive_rag.enabled}
              />

              <TechniqueSwitch
                label={TECHNIQUE_NAMES.caching}
                description={TECHNIQUE_DESCRIPTIONS.caching}
                checked={config.caching.enabled}
                onCheckedChange={(checked) => handleTechniqueToggle('caching', checked)}
              />

              <TechniqueSwitch
                label={TECHNIQUE_NAMES.hybrid_search}
                description={TECHNIQUE_DESCRIPTIONS.hybrid_search}
                checked={config.hybrid_search.enabled}
                onCheckedChange={(checked) => handleTechniqueToggle('hybrid_search', checked)}
                disabled={!config.naive_rag.enabled}
              />

              <TechniqueSwitch
                label={TECHNIQUE_NAMES.memory}
                description={TECHNIQUE_DESCRIPTIONS.memory}
                checked={config.memory.enabled}
                onCheckedChange={(checked) => handleTechniqueToggle('memory', checked)}
              />
            </div>
          </TabsContent>

          {/* Advanced Tab */}
          <TabsContent value="advanced" className="space-y-4">
            <Accordion type="multiple" className="w-full">
              {/* Naive RAG Settings */}
              {config.naive_rag.enabled && (
                <AccordionItem value="naive_rag">
                  <AccordionTrigger>Naive RAG Configuration</AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>Chunk Size: {config.naive_rag.chunk_size}</Label>
                      <Slider
                        value={[config.naive_rag.chunk_size]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.naive_rag.chunk_size = value
                          onConfigChange(newConfig)
                        }}
                        min={128}
                        max={2048}
                        step={128}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Chunk Overlap: {config.naive_rag.chunk_overlap}</Label>
                      <Slider
                        value={[config.naive_rag.chunk_overlap]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.naive_rag.chunk_overlap = value
                          onConfigChange(newConfig)
                        }}
                        min={0}
                        max={512}
                        step={10}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Top K Documents: {config.naive_rag.top_k}</Label>
                      <Slider
                        value={[config.naive_rag.top_k]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.naive_rag.top_k = value
                          onConfigChange(newConfig)
                        }}
                        min={1}
                        max={20}
                        step={1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Similarity Threshold: {config.naive_rag.similarity_threshold.toFixed(2)}</Label>
                      <Slider
                        value={[config.naive_rag.similarity_threshold]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.naive_rag.similarity_threshold = value
                          onConfigChange(newConfig)
                        }}
                        min={0}
                        max={1}
                        step={0.05}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* RAG-as-tool Settings */}
              {config.rag_tool.enabled && (
                <AccordionItem value="rag_tool">
                  <AccordionTrigger>RAG-as-tool Configuration</AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>Tool Name</Label>
                      <Input
                        value={config.rag_tool.tool_name}
                        onChange={(e) => {
                          const newConfig = { ...config }
                          newConfig.rag_tool.tool_name = e.target.value
                          onConfigChange(newConfig)
                        }}
                        placeholder="search_knowledge_base"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Tool Description</Label>
                      <Input
                        value={config.rag_tool.tool_description}
                        onChange={(e) => {
                          const newConfig = { ...config }
                          newConfig.rag_tool.tool_description = e.target.value
                          onConfigChange(newConfig)
                        }}
                        placeholder="Search the knowledge base for relevant information"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Chunk Size: {config.rag_tool.chunk_size}</Label>
                      <Slider
                        value={[config.rag_tool.chunk_size]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.rag_tool.chunk_size = value
                          onConfigChange(newConfig)
                        }}
                        min={128}
                        max={2048}
                        step={128}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Chunk Overlap: {config.rag_tool.chunk_overlap}</Label>
                      <Slider
                        value={[config.rag_tool.chunk_overlap]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.rag_tool.chunk_overlap = value
                          onConfigChange(newConfig)
                        }}
                        min={0}
                        max={512}
                        step={10}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Top K Documents: {config.rag_tool.top_k}</Label>
                      <Slider
                        value={[config.rag_tool.top_k]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.rag_tool.top_k = value
                          onConfigChange(newConfig)
                        }}
                        min={1}
                        max={20}
                        step={1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Similarity Threshold: {config.rag_tool.similarity_threshold.toFixed(2)}</Label>
                      <Slider
                        value={[config.rag_tool.similarity_threshold]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.rag_tool.similarity_threshold = value
                          onConfigChange(newConfig)
                        }}
                        min={0}
                        max={1}
                        step={0.05}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Compression Settings */}
              {config.compression.enabled && (
                <AccordionItem value="compression">
                  <AccordionTrigger>Compression Configuration</AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>Compression Ratio: {config.compression.compression_ratio.toFixed(2)}</Label>
                      <Slider
                        value={[config.compression.compression_ratio]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.compression.compression_ratio = value
                          onConfigChange(newConfig)
                        }}
                        min={0.1}
                        max={0.9}
                        step={0.1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Max Compressed Tokens: {config.compression.max_compressed_tokens}</Label>
                      <Slider
                        value={[config.compression.max_compressed_tokens]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.compression.max_compressed_tokens = value
                          onConfigChange(newConfig)
                        }}
                        min={512}
                        max={4096}
                        step={256}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Reranking Settings */}
              {config.reranking.enabled && (
                <AccordionItem value="reranking">
                  <AccordionTrigger>Reranking Configuration</AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>Top N After Rerank: {config.reranking.top_n_after_rerank}</Label>
                      <Slider
                        value={[config.reranking.top_n_after_rerank]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.reranking.top_n_after_rerank = value
                          onConfigChange(newConfig)
                        }}
                        min={1}
                        max={10}
                        step={1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Rerank Threshold: {config.reranking.rerank_threshold.toFixed(2)}</Label>
                      <Slider
                        value={[config.reranking.rerank_threshold]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.reranking.rerank_threshold = value
                          onConfigChange(newConfig)
                        }}
                        min={0}
                        max={1}
                        step={0.05}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Caching Settings */}
              {config.caching.enabled && (
                <AccordionItem value="caching">
                  <AccordionTrigger>Caching Configuration</AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>Similarity Threshold: {config.caching.similarity_threshold.toFixed(2)}</Label>
                      <Slider
                        value={[config.caching.similarity_threshold]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.caching.similarity_threshold = value
                          onConfigChange(newConfig)
                        }}
                        min={0.8}
                        max={1.0}
                        step={0.01}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Max Cache Size: {config.caching.max_cache_size}</Label>
                      <Input
                        type="number"
                        value={config.caching.max_cache_size}
                        onChange={(e) => {
                          const newConfig = { ...config }
                          newConfig.caching.max_cache_size = parseInt(e.target.value) || 1000
                          onConfigChange(newConfig)
                        }}
                        min={100}
                        max={10000}
                        step={100}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>TTL (seconds): {config.caching.ttl_seconds}</Label>
                      <Input
                        type="number"
                        value={config.caching.ttl_seconds}
                        onChange={(e) => {
                          const newConfig = { ...config }
                          newConfig.caching.ttl_seconds = parseInt(e.target.value) || 3600
                          onConfigChange(newConfig)
                        }}
                        min={60}
                        max={86400}
                        step={60}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Hybrid Search Settings */}
              {config.hybrid_search.enabled && (
                <AccordionItem value="hybrid_search">
                  <AccordionTrigger>Hybrid Search Configuration</AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>BM25 Weight: {config.hybrid_search.bm25_weight.toFixed(2)}</Label>
                      <Slider
                        value={[config.hybrid_search.bm25_weight]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.hybrid_search.bm25_weight = value
                          newConfig.hybrid_search.vector_weight = 1.0 - value
                          onConfigChange(newConfig)
                        }}
                        min={0}
                        max={1}
                        step={0.1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Vector Weight: {config.hybrid_search.vector_weight.toFixed(2)}</Label>
                      <Slider
                        value={[config.hybrid_search.vector_weight]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.hybrid_search.vector_weight = value
                          newConfig.hybrid_search.bm25_weight = 1.0 - value
                          onConfigChange(newConfig)
                        }}
                        min={0}
                        max={1}
                        step={0.1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Top K Per Method: {config.hybrid_search.top_k_per_method}</Label>
                      <Slider
                        value={[config.hybrid_search.top_k_per_method]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.hybrid_search.top_k_per_method = value
                          onConfigChange(newConfig)
                        }}
                        min={1}
                        max={20}
                        step={1}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Memory Settings */}
              {config.memory.enabled && (
                <AccordionItem value="memory">
                  <AccordionTrigger>Memory Configuration</AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>Max Conversation Turns: {config.memory.max_conversation_turns}</Label>
                      <Slider
                        value={[config.memory.max_conversation_turns]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.memory.max_conversation_turns = value
                          onConfigChange(newConfig)
                        }}
                        min={1}
                        max={20}
                        step={1}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Summary Trigger Turns: {config.memory.summary_trigger_turns}</Label>
                      <Slider
                        value={[config.memory.summary_trigger_turns]}
                        onValueChange={([value]) => {
                          const newConfig = { ...config }
                          newConfig.memory.summary_trigger_turns = value
                          onConfigChange(newConfig)
                        }}
                        min={1}
                        max={10}
                        step={1}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

interface TechniqueSwitchProps {
  label: string
  description: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  disabled?: boolean
}

function TechniqueSwitch({ label, description, checked, onCheckedChange, disabled }: TechniqueSwitchProps) {
  return (
    <div className="flex items-start justify-between space-x-4 p-3 border rounded-lg">
      <div className="flex-1 space-y-1">
        <Label className={disabled ? 'text-muted-foreground' : ''}>{label}</Label>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} disabled={disabled} />
    </div>
  )
}

