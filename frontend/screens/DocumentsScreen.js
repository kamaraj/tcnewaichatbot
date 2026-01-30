import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { listDocuments } from '../api/client';

export default function DocumentsScreen() {
    const [documents, setDocuments] = useState([]);
    const [refreshing, setRefreshing] = useState(false);
    const [loading, setLoading] = useState(true);

    const loadDocs = useCallback(async () => {
        try {
            const data = await listDocuments();
            setDocuments(data);
        } catch (e) {
            console.error('Failed to load documents:', e);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadDocs();
    }, [loadDocs]);

    const onRefresh = () => {
        setRefreshing(true);
        loadDocs();
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return '#10b981';
            case 'processing': return '#6366f1';
            case 'pending': return '#f59e0b';
            case 'failed': return '#ef4444';
            default: return '#94a3b8';
        }
    };

    const formatBytes = (bytes) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const renderItem = ({ item }) => (
        <View style={styles.docCard}>
            <View style={styles.docHeader}>
                <Text style={styles.docIcon}>📄</Text>
                <View style={styles.docInfo}>
                    <Text style={styles.docName} numberOfLines={1}>{item.filename}</Text>
                    <Text style={styles.docMeta}>
                        {formatBytes(item.file_size_bytes)} • {item.num_pages} pages
                    </Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: `${getStatusColor(item.processing_status)}20` }]}>
                    <Text style={[styles.statusText, { color: getStatusColor(item.processing_status) }]}>
                        {item.processing_status}
                    </Text>
                </View>
            </View>

            <View style={styles.metricsRow}>
                <View style={styles.metric}>
                    <Text style={styles.metricValue}>{item.num_chunks}</Text>
                    <Text style={styles.metricLabel}>Chunks</Text>
                </View>
                <View style={styles.metric}>
                    <Text style={styles.metricValue}>{item.metrics?.chunking_time_ms || 0}ms</Text>
                    <Text style={styles.metricLabel}>Chunking</Text>
                </View>
                <View style={styles.metric}>
                    <Text style={styles.metricValue}>{item.metrics?.embedding_time_ms || 0}ms</Text>
                    <Text style={styles.metricLabel}>Embedding</Text>
                </View>
                <View style={styles.metric}>
                    <Text style={styles.metricValue}>{item.metrics?.total_processing_time_ms || 0}ms</Text>
                    <Text style={styles.metricLabel}>Total</Text>
                </View>
            </View>
        </View>
    );

    return (
        <View style={styles.container}>
            <FlatList
                data={documents}
                renderItem={renderItem}
                keyExtractor={(item) => item.id.toString()}
                contentContainerStyle={styles.list}
                refreshControl={
                    <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
                }
                ListEmptyComponent={
                    <View style={styles.emptyContainer}>
                        <Text style={styles.emptyIcon}>📂</Text>
                        <Text style={styles.emptyText}>No documents uploaded yet</Text>
                        <Text style={styles.emptySubtext}>Upload PDFs to get started</Text>
                    </View>
                }
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0f172a',
    },
    list: {
        padding: 16,
    },
    docCard: {
        backgroundColor: '#1e293b',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: '#334155',
    },
    docHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    docIcon: {
        fontSize: 32,
        marginRight: 12,
    },
    docInfo: {
        flex: 1,
    },
    docName: {
        color: '#f1f5f9',
        fontSize: 16,
        fontWeight: '600',
    },
    docMeta: {
        color: '#94a3b8',
        fontSize: 12,
        marginTop: 2,
    },
    statusBadge: {
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
    },
    statusText: {
        fontSize: 12,
        fontWeight: '600',
        textTransform: 'capitalize',
    },
    metricsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        backgroundColor: '#0f172a',
        borderRadius: 8,
        padding: 12,
    },
    metric: {
        alignItems: 'center',
    },
    metricValue: {
        color: '#6366f1',
        fontSize: 14,
        fontWeight: '700',
    },
    metricLabel: {
        color: '#94a3b8',
        fontSize: 10,
        marginTop: 2,
    },
    emptyContainer: {
        alignItems: 'center',
        paddingVertical: 60,
    },
    emptyIcon: {
        fontSize: 48,
        marginBottom: 16,
    },
    emptyText: {
        color: '#f1f5f9',
        fontSize: 18,
        fontWeight: '600',
    },
    emptySubtext: {
        color: '#94a3b8',
        fontSize: 14,
        marginTop: 4,
    },
});
