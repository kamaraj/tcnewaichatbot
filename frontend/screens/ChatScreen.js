import React, { useState } from 'react';
import {
    View, Text, StyleSheet, TextInput, FlatList, TouchableOpacity,
    KeyboardAvoidingView, Platform, ActivityIndicator
} from 'react-native';
import { chatWithBot } from '../api/client';

export default function ChatScreen() {
    const [messages, setMessages] = useState([
        {
            id: '0',
            text: 'Hello! Ask me questions about your documents. I will only answer based on what\'s in the uploaded PDFs.',
            sender: 'bot',
            confidence: null
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMsg = { id: Date.now().toString(), text: input, sender: 'user' };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const response = await chatWithBot(userMsg.text);
            const botMsg = {
                id: (Date.now() + 1).toString(),
                text: response.answer,
                sender: 'bot',
                confidence: response.confidence,
                metrics: response.metrics,
                sources: response.sources
            };
            setMessages(prev => [...prev, botMsg]);
        } catch (error) {
            const errorMsg = {
                id: (Date.now() + 1).toString(),
                text: "Sorry, I couldn't reach the server. Please try again.",
                sender: 'bot',
                error: true
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    const getConfidenceColor = (confidence) => {
        switch (confidence) {
            case 'high': return '#10b981';
            case 'medium': return '#f59e0b';
            case 'low': return '#ef4444';
            default: return '#94a3b8';
        }
    };

    const renderItem = ({ item }) => (
        <View style={[
            styles.messageContainer,
            item.sender === 'user' ? styles.userContainer : styles.botContainer
        ]}>
            <View style={[
                styles.bubble,
                item.sender === 'user' ? styles.userBubble : styles.botBubble,
                item.error && styles.errorBubble
            ]}>
                <Text style={[
                    styles.text,
                    item.sender === 'user' ? styles.userText : styles.botText
                ]}>{item.text}</Text>
            </View>

            {item.sender === 'bot' && item.confidence && (
                <View style={styles.metaRow}>
                    <View style={[styles.confidenceBadge, { backgroundColor: `${getConfidenceColor(item.confidence)}20` }]}>
                        <Text style={[styles.confidenceText, { color: getConfidenceColor(item.confidence) }]}>
                            {item.confidence} confidence
                        </Text>
                    </View>
                    {item.metrics && (
                        <Text style={styles.metricsText}>
                            ⚡ {item.metrics.total_time_ms}ms • 🔍 {item.metrics.chunks_retrieved} chunks
                        </Text>
                    )}
                </View>
            )}

            {item.sender === 'bot' && item.sources && item.sources.length > 0 && (
                <View style={styles.sourcesRow}>
                    <Text style={styles.sourcesLabel}>Sources: </Text>
                    <Text style={styles.sourcesText}>{item.sources.join(', ')}</Text>
                </View>
            )}
        </View>
    );

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.container}
            keyboardVerticalOffset={90}
        >
            <FlatList
                data={messages}
                renderItem={renderItem}
                keyExtractor={item => item.id}
                contentContainerStyle={styles.listContent}
            />

            {loading && (
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="small" color="#6366f1" />
                    <Text style={styles.loadingText}>Searching documents...</Text>
                </View>
            )}

            <View style={styles.inputContainer}>
                <TextInput
                    style={styles.input}
                    value={input}
                    onChangeText={setInput}
                    placeholder="Ask about your documents..."
                    placeholderTextColor="#64748b"
                    multiline
                />
                <TouchableOpacity
                    onPress={sendMessage}
                    style={[styles.sendButton, loading && styles.sendButtonDisabled]}
                    disabled={loading}
                >
                    <Text style={styles.sendButtonText}>Send</Text>
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0f172a',
    },
    listContent: {
        padding: 16,
        paddingBottom: 20
    },
    messageContainer: {
        marginBottom: 16,
    },
    userContainer: {
        alignItems: 'flex-end',
    },
    botContainer: {
        alignItems: 'flex-start',
    },
    bubble: {
        maxWidth: '85%',
        padding: 14,
        borderRadius: 16,
    },
    userBubble: {
        backgroundColor: '#6366f1',
        borderBottomRightRadius: 4,
    },
    botBubble: {
        backgroundColor: '#1e293b',
        borderBottomLeftRadius: 4,
        borderWidth: 1,
        borderColor: '#334155',
    },
    errorBubble: {
        backgroundColor: '#ef444420',
        borderColor: '#ef4444',
    },
    text: {
        fontSize: 15,
        lineHeight: 22,
    },
    userText: {
        color: 'white',
    },
    botText: {
        color: '#f1f5f9',
    },
    metaRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 8,
        flexWrap: 'wrap',
    },
    confidenceBadge: {
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 10,
        marginRight: 8,
    },
    confidenceText: {
        fontSize: 11,
        fontWeight: '600',
        textTransform: 'capitalize',
    },
    metricsText: {
        fontSize: 11,
        color: '#94a3b8',
    },
    sourcesRow: {
        flexDirection: 'row',
        marginTop: 6,
        flexWrap: 'wrap',
    },
    sourcesLabel: {
        fontSize: 11,
        color: '#64748b',
    },
    sourcesText: {
        fontSize: 11,
        color: '#6366f1',
        flex: 1,
    },
    inputContainer: {
        flexDirection: 'row',
        padding: 12,
        borderTopWidth: 1,
        borderTopColor: '#334155',
        backgroundColor: '#1e293b',
        alignItems: 'flex-end'
    },
    input: {
        flex: 1,
        backgroundColor: '#0f172a',
        borderRadius: 12,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderWidth: 1,
        borderColor: '#334155',
        marginRight: 10,
        fontSize: 15,
        color: '#f1f5f9',
        maxHeight: 100,
    },
    sendButton: {
        backgroundColor: '#6366f1',
        paddingHorizontal: 20,
        paddingVertical: 12,
        borderRadius: 12,
    },
    sendButtonDisabled: {
        backgroundColor: '#4b5563',
    },
    sendButtonText: {
        color: 'white',
        fontWeight: '600',
    },
    loadingContainer: {
        flexDirection: 'row',
        marginLeft: 16,
        marginBottom: 10,
        alignItems: 'center'
    },
    loadingText: {
        marginLeft: 8,
        color: '#94a3b8',
        fontSize: 12
    }
});
