"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Car, Settings, Rocket, Info } from "lucide-react";
import Image from "next/image";

const formSchema = z.object({
  dataset: z.string().min(1, "请选择数据集类型"),
  file_id: z.number().min(1, "文件ID必须大于0"),
  dataset_path: z.string().min(1, "请输入数据集路径"),
  map_path: z.string().min(1, "请输入地图文件路径"),
  stamp_start: z.number().optional(),
  stamp_end: z.number().optional(),
  perception_range: z.number().min(10).max(200),
  frame_step: z.number().min(1).max(100),
});

type FormData = z.infer<typeof formSchema>;

const datasetInfo: Record<string, string> = {
  argoverse2: "支持自动驾驶场景，包含高精度传感器数据",
  dlp: "停车场景专用数据集，适合泊车算法研究",
  highD: "高速公路场景，包含车道变换和跟车行为",
  inD: "交叉路口场景，适合交通冲突分析",
  rounD: "环形交叉口场景数据",
  exiD: "高速公路出入口场景",
  interaction: "复杂交互场景数据集",
  nuplan: "大规模城市驾驶数据集",
  womd: "Waymo开放运动数据集，包含多样化驾驶场景",
};

const datasetOptions = [
  { value: "argoverse2", label: "Argoverse 2" },
  { value: "dlp", label: "Dragon Lake Parking (DLP)" },
  { value: "highD", label: "HighD" },
  { value: "inD", label: "InD" },
  { value: "rounD", label: "RounD" },
  { value: "exiD", label: "ExiD" },
  { value: "interaction", label: "INTERACTION" },
  { value: "nuplan", label: "NuPlan" },
  { value: "womd", label: "Waymo Open Motion Dataset" },
];

interface MapFile {
  id: string;
  path: string;
  name: string;
}

interface DatasetFile {
  file_id: number;
  dataset_path: string;
  preview_image: string | null;
  has_tracks: boolean;
  has_meta: boolean;
  duration_ms?: number | null;
}

export default function DatasetConfigPage() {
  const [statusMessage, setStatusMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);
  const [mapFiles, setMapFiles] = useState<MapFile[]>([]);
  const [datasetFiles, setDatasetFiles] = useState<
    Record<string, DatasetFile[]>
  >({});
  const [selectedPreviewImage, setSelectedPreviewImage] = useState<
    string | null
  >(null);
  const router = useRouter();

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      dataset: "",
      file_id: 1,
      dataset_path: "",
      map_path: "",
      perception_range: 30,
      frame_step: 1,
      stamp_start: 0,
      stamp_end: 30000, // 默认结束时间 30000ms
    },
  });

  const selectedDataset = form.watch("dataset");
  const selectedFileId = form.watch("file_id");
  const [maxStampMs, setMaxStampMs] = useState<number>(30000);

  // 加载文件列表
  useEffect(() => {
    const loadFiles = async () => {
      try {
        setIsLoadingFiles(true);
        const response = await fetch("http://localhost:8000/api/data/files");
        if (!response.ok) throw new Error("Failed to load files");
        const data = await response.json();
        setMapFiles(data.maps || []);
        setDatasetFiles(data.datasets || {});

        // 设置默认值
        if (data.maps && data.maps.length > 0) {
          form.setValue("map_path", data.maps[0].path);
        }
      } catch (error) {
        console.error("加载文件列表失败:", error);
        setStatusMessage("⚠️ 无法加载文件列表，请手动输入路径");
      } finally {
        setIsLoadingFiles(false);
      }
    };
    loadFiles();
  }, [form]);

  // 当数据集类型改变时，更新可用文件列表和预览图
  useEffect(() => {
    if (selectedDataset && datasetFiles[selectedDataset]) {
      const files = datasetFiles[selectedDataset];
      if (files.length > 0) {
        const firstFile = files[0];
        form.setValue("file_id", firstFile.file_id);
        form.setValue("dataset_path", firstFile.dataset_path);
        setSelectedPreviewImage(firstFile.preview_image);
        const dur = firstFile.duration_ms ?? 30000;
        const durMs = Math.max(1000, Math.floor(dur));
        setMaxStampMs(durMs);
        // 确保当前表单值在范围内
        form.setValue("stamp_start", 0);
        form.setValue(
          "stamp_end",
          Math.min(form.getValues("stamp_end") ?? 30000, durMs)
        );
      }
    }
  }, [selectedDataset, datasetFiles, form]);

  // 当文件ID改变时，更新预览图
  useEffect(() => {
    if (selectedDataset && selectedFileId && datasetFiles[selectedDataset]) {
      const file = datasetFiles[selectedDataset].find(
        (f) => f.file_id === selectedFileId
      );
      if (file) {
        setSelectedPreviewImage(file.preview_image);
        form.setValue("dataset_path", file.dataset_path);
        const dur = file.duration_ms ?? 30000;
        const durMs = Math.max(1000, Math.floor(dur));
        setMaxStampMs(durMs);
        // 把 stamp_end clamp 到合法范围
        const curStart = form.getValues("stamp_start") ?? 0;
        const curEnd = form.getValues("stamp_end") ?? durMs;
        const nextStart = Math.max(0, Math.min(curStart, durMs));
        const nextEnd = Math.max(nextStart, Math.min(curEnd, durMs));
        form.setValue("stamp_start", nextStart);
        form.setValue("stamp_end", nextEnd);
      }
    }
  }, [selectedFileId, selectedDataset, datasetFiles, form]);

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    setStatusMessage("");

    try {
      // 发送数据到FastAPI后端
      const response = await fetch(
        "http://localhost:8000/api/simulation/initialize",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            dataset: data.dataset,
            file_id: data.file_id,
            dataset_path: data.dataset_path,
            map_path: data.map_path,
            // ⚠️ 确保时间戳范围始终发送（使用默认值如果未设置）
            stamp_start: data.stamp_start ?? 0,
            stamp_end: data.stamp_end ?? maxStampMs,
            perception_range: data.perception_range,
            frame_step: data.frame_step,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      // 检查是否成功获取到session_id
      if (!result.session_id) {
        throw new Error("后端没有返回session_id");
      }

      setStatusMessage(
        `✅ 会话创建成功！会话ID: ${result.session_id} 正在跳转到控制台...`
      );

      // 等待一下让用户看到成功消息，然后跳转到dashboard并传递session_id
      setTimeout(() => {
        router.push(`/dashboard?session_id=${result.session_id}`);
      }, 1500);
    } catch (error) {
      console.error("Error submitting form:", error);
      setStatusMessage("❌ 处理失败，请检查配置参数和后端服务");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Car className="h-8 w-8 text-white" />
            </div>
            <Image
              src="/logo2.jpg"
              alt="Tactics2D Logo"
              width={200}
              height={64}
              className="h-16 w-auto"
            />
          </div>
          <p className="text-lg text-gray-600">
            配置轨迹数据集和地图参数，开始数据处理
          </p>
        </div>

        <Card className="shadow-xl border-0 backdrop-blur-sm">
          <CardHeader className="pb-6">
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Settings className="h-6 w-6 text-blue-600" />
              数据集配置
            </CardTitle>
            <CardDescription className="text-base">
              选择数据集类型并配置相关参数，系统将自动处理轨迹数据
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8"
              >
                {/* Basic Configuration */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <FormField
                    control={form.control}
                    name="dataset"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-base font-semibold">
                          数据集类型
                        </FormLabel>

                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="h-12">
                              <SelectValue placeholder="请选择数据集类型" />
                            </SelectTrigger>
                          </FormControl>

                          <SelectContent>
                            {datasetOptions.map((option) => (
                              <SelectItem
                                key={option.value}
                                value={option.value}
                              >
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <FormMessage />

                        {field.value && (
                          <Alert className="mt-2">
                            <Info className="h-4 w-4" />
                            <AlertDescription>
                              {datasetInfo[field.value]}
                            </AlertDescription>
                          </Alert>
                        )}
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="file_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-base font-semibold">
                          数据文件
                        </FormLabel>
                        <Select
                          onValueChange={(value) => {
                            const fileId = parseInt(value);
                            field.onChange(fileId);
                          }}
                          value={field.value?.toString()}
                          disabled={!selectedDataset || isLoadingFiles}
                        >
                          <FormControl>
                            <SelectTrigger className="h-12">
                              <SelectValue
                                placeholder={
                                  isLoadingFiles
                                    ? "加载中..."
                                    : "请先选择数据集类型"
                                }
                              />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {selectedDataset &&
                              datasetFiles[selectedDataset]?.map((file) => (
                                <SelectItem
                                  key={file.file_id}
                                  value={file.file_id.toString()}
                                >
                                  文件{" "}
                                  {file.file_id.toString().padStart(2, "0")}
                                  {file.has_tracks && file.has_meta ? " ✓" : ""}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          选择要处理的数据文件编号
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* 预览图显示 */}
                {selectedPreviewImage && (
                  <Card className="border-2 border-blue-200 bg-blue-50/50">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        <div className="flex-shrink-0 relative w-32 h-24">
                          <Image
                            src={`http://localhost:8000${selectedPreviewImage}`}
                            alt="场景预览"
                            fill
                            className="object-cover rounded-lg border-2 border-blue-300"
                            unoptimized
                            onError={(e) => {
                              e.currentTarget.style.display = "none";
                            }}
                          />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-gray-700 mb-1">
                            📸 场景预览
                          </p>
                          <p className="text-xs text-gray-600">
                            这是所选数据文件的场景预览图
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Path Configuration */}
                <div className="space-y-6">
                  <FormField
                    control={form.control}
                    name="map_path"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-base font-semibold">
                          地图文件
                        </FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                          disabled={isLoadingFiles}
                        >
                          <FormControl>
                            <SelectTrigger className="h-12">
                              <SelectValue
                                placeholder={
                                  isLoadingFiles
                                    ? "加载中..."
                                    : "请选择地图文件"
                                }
                              />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {mapFiles.map((map) => (
                              <SelectItem key={map.id} value={map.path}>
                                {map.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          选择 OpenStreetMap (.osm) 格式的地图文件
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* 隐藏的 dataset_path 字段（自动填充） */}
                  <FormField
                    control={form.control}
                    name="dataset_path"
                    render={({ field }) => (
                      <FormItem className="hidden">
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>

                {/* Advanced Parameters */}
                <Card className="border-2 border-dashed border-gray-200">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Settings className="h-5 w-5 text-purple-600" />
                      高级参数配置
                    </CardTitle>
                    <CardDescription>调整数据处理的详细参数</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Timestamp Range */}
                    <div className="space-y-6">
                      <FormField
                        control={form.control}
                        name="stamp_start"
                        render={({ field: startField }) => (
                          <FormField
                            control={form.control}
                            name="stamp_end"
                            render={({ field: endField }) => (
                              <FormItem>
                                <FormLabel className="text-base font-semibold">
                                  时间戳范围 (毫秒)
                                </FormLabel>
                                <FormControl>
                                  <div className="space-y-4">
                                    <Slider
                                      min={0}
                                      max={maxStampMs}
                                      step={100}
                                      value={[
                                        startField.value ?? 0,
                                        endField.value ?? maxStampMs,
                                      ]}
                                      onValueChange={(values) => {
                                        // ⚠️ 修复：0 是有效值，不应该转换为 undefined
                                        // 只有当值明确被设置为 null/undefined 时才不发送
                                        startField.onChange(values[0]);
                                        endField.onChange(values[1]);
                                      }}
                                      className="w-full"
                                    />
                                    <div className="flex justify-between text-sm">
                                      <div className="text-gray-500">
                                        <span>最小: 0</span>
                                      </div>
                                      <div className="flex gap-4 font-medium">
                                        <span className="text-blue-600">
                                          起始: {startField.value ?? 0}ms
                                        </span>
                                        <span className="text-purple-600">
                                          结束: {endField.value ?? maxStampMs}ms
                                        </span>
                                      </div>
                                      <div className="text-gray-500">
                                        <span>最大: {maxStampMs}ms</span>
                                      </div>
                                    </div>
                                  </div>
                                </FormControl>
                                <FormDescription>
                                  拖动滑块设置时间戳范围（最大值来自对应的
                                  <code className="px-1">
                                    *_recordingMeta.csv
                                  </code>
                                  的 <code className="px-1">duration</code>）
                                </FormDescription>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        )}
                      />
                    </div>

                    {/* Processing Parameters */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <FormField
                        control={form.control}
                        name="perception_range"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-base font-semibold">
                              感知范围 (米)
                            </FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min="10"
                                max="200"
                                step="5"
                                className="h-12"
                                placeholder="输入感知范围 (10-200米)"
                                {...field}
                                onChange={(e) =>
                                  field.onChange(parseInt(e.target.value) || 50)
                                }
                              />
                            </FormControl>
                            <FormDescription>
                              车辆感知周围环境的范围 (10-200米)
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="frame_step"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-base font-semibold">
                              帧步长
                            </FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min="1"
                                max="100"
                                step="1"
                                className="h-12"
                                placeholder="输入帧步长 (1-100)"
                                {...field}
                                onChange={(e) =>
                                  field.onChange(parseInt(e.target.value) || 1)
                                }
                              />
                            </FormControl>
                            <FormDescription>
                              数据处理的帧间隔步长 (1-100)
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </CardContent>
                </Card>

                <Button
                  type="submit"
                  className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 transition-all duration-200"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-3"></div>
                      处理中...
                    </>
                  ) : (
                    <>
                      <Rocket className="mr-3 h-5 w-5" />
                      开始处理数据
                    </>
                  )}
                </Button>

                {statusMessage && (
                  <Alert
                    className={`${
                      statusMessage.includes("✅")
                        ? "border-green-200 bg-green-50 text-green-800"
                        : "border-red-200 bg-red-50 text-red-800"
                    } text-center`}
                  >
                    <AlertDescription className="font-medium text-base">
                      {statusMessage}
                    </AlertDescription>
                  </Alert>
                )}
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
