/**
 * Data sources API — the customer databases this deployment can read.
 */

import apiClient from './client';
import type {
  DataSource,
  DataSourceCreate,
  DataSourceTestResult,
} from '../types';

export async function fetchDataSources(): Promise<DataSource[]> {
  const { data } = await apiClient.get<DataSource[]>('/data-sources/');
  return data;
}

export async function createDataSource(
  payload: DataSourceCreate,
): Promise<DataSource> {
  const { data } = await apiClient.post<DataSource>('/data-sources/', payload);
  return data;
}

export async function updateDataSource(
  id: string,
  payload: Partial<DataSourceCreate>,
): Promise<DataSource> {
  const { data } = await apiClient.patch<DataSource>(`/data-sources/${id}`, payload);
  return data;
}

export async function deleteDataSource(id: string): Promise<void> {
  await apiClient.delete(`/data-sources/${id}`);
}

export async function testDataSource(id: string): Promise<DataSourceTestResult> {
  const { data } = await apiClient.post<DataSourceTestResult>(
    `/data-sources/${id}/test`,
  );
  return data;
}
