import 'react-native-gesture-handler';
import React, { useState, useEffect, useCallback } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'expo-status-bar';
import {
    View, Text, StyleSheet, TouchableOpacity, ScrollView,
    RefreshControl, ActivityIndicator
} from 'react-native';

import UploadScreen from './screens/UploadScreen';
import ChatScreen from './screens/ChatScreen';
import DocumentsScreen from './screens/DocumentsScreen';
import { getDashboardStats } from './api/client';

const Stack = createStackNavigator();

function DashboardScreen({ navigation }) {
    const [stats, setStats] = useState(null);
    const [refreshing, setRefreshing] = useState(false);
    const [loading, setLoading] = useState(true);

    const loadStats = useCallback(async () => {
        try {
            const data = await getDashboardStats();
            setStats(data);
        } catch (e) {
            console.error('Failed to load stats:', e);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadStats();
        const interval = setInterval(loadStats, 10000); // Refresh every 10s
        return () => clearInterval(interval);
    }, [loadStats]);

    const onRefresh = () => {
        setRefreshing(true);
        loadStats();
    };

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#6366f1" />
                <Text style={styles.loadingText}>Loading Dashboard...</Text>
            </View>
        );
    }

    return (
        <ScrollView
            style={styles.container}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        >
            <View style={styles.header}>
                <View>
                    <Text style={styles.headerTitle}>TCBot Enterprise</Text>
                    <Text style={styles.headerSubtitle}>RAG AI Platform</Text>
                </View>
                <View style={styles.statusBadge}>
                    <View style={styles.statusDot} />
                    <Text style={styles.statusText}>Online</Text>
                </View>
            </View>

            {/* Stats Grid */}
            <View style={styles.statsGrid}>
                <StatCard
                    icon="📄"
                    value={stats?.documents?.total || 0}
                    label="Documents"
                    subtext={`${stats?.documents?.success_rate || 0}% success`}
                    color="#6366f1"
                />
                <StatCard
                    icon="🧩"
                    value={stats?.content?.total_chunks || 0}
                    label="Chunks"
                    subtext={`${stats?.content?.avg_chunks_per_doc || 0} avg/doc`}
                    color="#10b981"
                />
                <StatCard
                    icon="💬"
                    value={stats?.query_performance?.total_queries || 0}
                    label="Queries"
                    subtext={`${stats?.query_performance?.avg_total_time_ms || 0}ms avg`}
                    color="#f59e0b"
                />
                <StatCard
                    icon="💾"
                    value={`${stats?.storage?.total_mb || 0}`}
                    label="MB Storage"
                    subtext={`${stats?.content?.total_pages || 0} pages`}
                    color="#3b82f6"
                />
            </View>

            {/* Quick Actions */}
            <Text style={styles.sectionTitle}>Quick Actions</Text>
            <View style={styles.actionsRow}>
                <TouchableOpacity
                    style={[styles.actionCard, { backgroundColor: '#6366f1' }]}
                    onPress={() => navigation.navigate('Upload')}
                >
                    <Text style={styles.actionIcon}>📤</Text>
                    <Text style={styles.actionText}>Upload PDF</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.actionCard, { backgroundColor: '#10b981' }]}
                    onPress={() => navigation.navigate('Chat')}
                >
                    <Text style={styles.actionIcon}>💬</Text>
                    <Text style={styles.actionText}>Chat</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.actionCard, { backgroundColor: '#f59e0b' }]}
                    onPress={() => navigation.navigate('Documents')}
                >
                    <Text style={styles.actionIcon}>📂</Text>
                    <Text style={styles.actionText}>Documents</Text>
                </TouchableOpacity>
            </View>

            {/* Performance Metrics */}
            <Text style={styles.sectionTitle}>Performance</Text>
            <View style={styles.metricsCard}>
                <View style={styles.metricRow}>
                    <MetricItem
                        label="Chunking"
                        value={`${stats?.processing_performance?.avg_chunking_time_ms || 0}ms`}
                    />
                    <MetricItem
                        label="Embedding"
                        value={`${stats?.processing_performance?.avg_embedding_time_ms || 0}ms`}
                    />
                    <MetricItem
                        label="Total"
                        value={`${stats?.processing_performance?.avg_total_time_ms || 0}ms`}
                    />
                </View>
                <View style={styles.divider} />
                <View style={styles.metricRow}>
                    <MetricItem
                        label="Retrieval"
                        value={`${stats?.query_performance?.avg_retrieval_time_ms || 0}ms`}
                    />
                    <MetricItem
                        label="Generation"
                        value={`${stats?.query_performance?.avg_generation_time_ms || 0}ms`}
                    />
                    <MetricItem
                        label="Response"
                        value={`${stats?.query_performance?.avg_total_time_ms || 0}ms`}
                    />
                </View>
            </View>

            {/* Recent Queries */}
            <Text style={styles.sectionTitle}>Recent Queries</Text>
            <View style={styles.queriesCard}>
                {stats?.recent_queries?.length > 0 ? (
                    stats.recent_queries.slice(0, 5).map((q, i) => (
                        <View key={i} style={styles.queryItem}>
                            <Text style={styles.queryText} numberOfLines={1}>{q.query}</Text>
                            <Text style={styles.queryTime}>{q.total_time_ms}ms</Text>
                        </View>
                    ))
                ) : (
                    <Text style={styles.emptyText}>No queries yet</Text>
                )}
            </View>

            <StatusBar style="light" />
        </ScrollView>
    );
}

function StatCard({ icon, value, label, subtext, color }) {
    return (
        <View style={styles.statCard}>
            <View style={styles.statHeader}>
                <View style={[styles.statIcon, { backgroundColor: `${color}20` }]}>
                    <Text style={{ fontSize: 20 }}>{icon}</Text>
                </View>
            </View>
            <Text style={styles.statValue}>{value}</Text>
            <Text style={styles.statLabel}>{label}</Text>
            <Text style={styles.statSubtext}>{subtext}</Text>
        </View>
    );
}

function MetricItem({ label, value }) {
    return (
        <View style={styles.metricItem}>
            <Text style={styles.metricValue}>{value}</Text>
            <Text style={styles.metricLabel}>{label}</Text>
        </View>
    );
}

export default function App() {
    return (
        <NavigationContainer>
            <Stack.Navigator
                initialRouteName="Dashboard"
                screenOptions={{
                    headerStyle: { backgroundColor: '#1e293b' },
                    headerTintColor: '#f1f5f9',
                    headerTitleStyle: { fontWeight: '600' },
                }}
            >
                <Stack.Screen
                    name="Dashboard"
                    component={DashboardScreen}
                    options={{ title: 'TCBot Enterprise' }}
                />
                <Stack.Screen
                    name="Upload"
                    component={UploadScreen}
                    options={{ title: 'Upload Documents' }}
                />
                <Stack.Screen
                    name="Chat"
                    component={ChatScreen}
                    options={{ title: 'Chat Assistant' }}
                />
                <Stack.Screen
                    name="Documents"
                    component={DocumentsScreen}
                    options={{ title: 'All Documents' }}
                />
            </Stack.Navigator>
        </NavigationContainer>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0f172a',
    },
    loadingContainer: {
        flex: 1,
        backgroundColor: '#0f172a',
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        color: '#94a3b8',
        marginTop: 12,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 20,
        paddingTop: 10,
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: '700',
        color: '#f1f5f9',
    },
    headerSubtitle: {
        fontSize: 14,
        color: '#94a3b8',
    },
    statusBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#10b98120',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
    },
    statusDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#10b981',
        marginRight: 6,
    },
    statusText: {
        color: '#10b981',
        fontSize: 12,
        fontWeight: '600',
    },
    statsGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        padding: 10,
    },
    statCard: {
        width: '47%',
        backgroundColor: '#1e293b',
        borderRadius: 12,
        padding: 16,
        margin: '1.5%',
        borderWidth: 1,
        borderColor: '#334155',
    },
    statHeader: {
        marginBottom: 12,
    },
    statIcon: {
        width: 40,
        height: 40,
        borderRadius: 10,
        justifyContent: 'center',
        alignItems: 'center',
    },
    statValue: {
        fontSize: 28,
        fontWeight: '700',
        color: '#f1f5f9',
    },
    statLabel: {
        fontSize: 14,
        color: '#94a3b8',
        marginTop: 4,
    },
    statSubtext: {
        fontSize: 12,
        color: '#10b981',
        marginTop: 4,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#f1f5f9',
        marginLeft: 20,
        marginTop: 20,
        marginBottom: 12,
    },
    actionsRow: {
        flexDirection: 'row',
        paddingHorizontal: 15,
    },
    actionCard: {
        flex: 1,
        marginHorizontal: 5,
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
    },
    actionIcon: {
        fontSize: 28,
        marginBottom: 8,
    },
    actionText: {
        color: 'white',
        fontWeight: '600',
        fontSize: 14,
    },
    metricsCard: {
        backgroundColor: '#1e293b',
        marginHorizontal: 20,
        borderRadius: 12,
        padding: 16,
        borderWidth: 1,
        borderColor: '#334155',
    },
    metricRow: {
        flexDirection: 'row',
        justifyContent: 'space-around',
    },
    metricItem: {
        alignItems: 'center',
        flex: 1,
    },
    metricValue: {
        fontSize: 18,
        fontWeight: '700',
        color: '#6366f1',
    },
    metricLabel: {
        fontSize: 12,
        color: '#94a3b8',
        marginTop: 4,
    },
    divider: {
        height: 1,
        backgroundColor: '#334155',
        marginVertical: 12,
    },
    queriesCard: {
        backgroundColor: '#1e293b',
        marginHorizontal: 20,
        marginBottom: 30,
        borderRadius: 12,
        padding: 16,
        borderWidth: 1,
        borderColor: '#334155',
    },
    queryItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 10,
        borderBottomWidth: 1,
        borderBottomColor: '#334155',
    },
    queryText: {
        color: '#f1f5f9',
        flex: 1,
        marginRight: 10,
    },
    queryTime: {
        color: '#6366f1',
        fontWeight: '600',
    },
    emptyText: {
        color: '#94a3b8',
        textAlign: 'center',
        padding: 20,
    },
});
